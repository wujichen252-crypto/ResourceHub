"""OpenAI 兼容模型网关

同一套客户端可对接 DeepSeek / 智谱 / 通义 / OpenAI 等兼容接口：
- stream_chat：SSE 流式对话，支持 tool_calls 增量聚合
- chat：非流式对话，供评测、LLM-as-judge、摘要等场景
- embed：批量文本向量化
"""

import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import settings
from app.core.errors import ErrorCode


class AIProviderError(Exception):
    """模型服务异常，携带业务错误码便于上层返回统一响应"""

    def __init__(self, message: str, code: int = ErrorCode.AI_PROVIDER_ERROR):
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(slots=True)
class ProviderEvent:
    """流式事件：token 文本 / 工具调用 / 结束用量"""

    kind: str
    text: str = ""
    tool_call: dict[str, Any] | None = None
    usage: dict[str, int] = field(default_factory=dict)
    finish_reason: str | None = None


@dataclass(slots=True)
class ChatResult:
    """非流式对话结果"""

    content: str
    tool_calls: list[dict[str, Any]]
    usage: dict[str, int]
    latency_ms: int


class OpenAICompatibleProvider:
    """OpenAI 兼容协议客户端"""

    def __init__(self, base_url: str, api_key: str, timeout: float = 60.0):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        model: str,
        temperature: float = 0.3,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[ProviderEvent]:
        """流式对话：逐 token 产出，工具调用在流结束时聚合产出"""
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
            "max_tokens": max_tokens or settings.AI_MAX_OUTPUT_TOKENS,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/chat/completions",
                    headers=self._headers,
                    json=payload,
                ) as response:
                    if response.status_code >= 400:
                        body = (await response.aread()).decode("utf-8", "ignore")[:300]
                        raise AIProviderError(f"模型服务返回 {response.status_code}：{body}")
                    async for event in self._iter_stream(response):
                        yield event
        except httpx.TimeoutException as exc:
            raise AIProviderError("模型服务响应超时") from exc
        except httpx.HTTPError as exc:
            raise AIProviderError(f"模型服务连接失败：{exc}") from exc

    async def _iter_stream(self, response: httpx.Response) -> AsyncIterator[ProviderEvent]:
        """解析 OpenAI 兼容的 SSE 数据流"""
        tool_calls: dict[int, dict[str, Any]] = {}
        usage: dict[str, int] = {}
        finish_reason: str | None = None

        async for line in response.aiter_lines():
            if not line or not line.startswith("data:"):
                continue
            raw = line[5:].strip()
            if raw == "[DONE]":
                break
            try:
                chunk = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if chunk.get("usage"):
                usage = self._normalize_usage(chunk["usage"])

            for choice in chunk.get("choices", []):
                delta = choice.get("delta") or {}
                content = delta.get("content")
                if content:
                    yield ProviderEvent(kind="token", text=content)
                self._merge_tool_calls(tool_calls, delta.get("tool_calls") or [])
                if choice.get("finish_reason"):
                    finish_reason = choice["finish_reason"]

        for call in tool_calls.values():
            yield ProviderEvent(kind="tool_call", tool_call=call)
        yield ProviderEvent(kind="done", usage=usage, finish_reason=finish_reason)

    @staticmethod
    def _merge_tool_calls(store: dict[int, dict[str, Any]], items: list[dict[str, Any]]) -> None:
        """按 index 聚合分片的工具调用参数"""
        for item in items:
            index = item.get("index", 0)
            slot = store.setdefault(
                index,
                {"id": "", "type": "function", "function": {"name": "", "arguments": ""}},
            )
            if item.get("id"):
                slot["id"] = item["id"]
            function = item.get("function") or {}
            if function.get("name"):
                slot["function"]["name"] += function["name"]
            if function.get("arguments"):
                slot["function"]["arguments"] += function["arguments"]

    async def chat(
        self,
        messages: list[dict[str, Any]],
        model: str,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> ChatResult:
        """非流式对话，用于评测与结构化判定"""
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
            "max_tokens": max_tokens or settings.AI_MAX_OUTPUT_TOKENS,
        }
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers=self._headers,
                    json=payload,
                )
                if response.status_code >= 400:
                    raise AIProviderError(
                        f"模型服务返回 {response.status_code}：{response.text[:300]}"
                    )
                data = response.json()
        except httpx.TimeoutException as exc:
            raise AIProviderError("模型服务响应超时") from exc
        except httpx.HTTPError as exc:
            raise AIProviderError(f"模型服务连接失败：{exc}") from exc

        message = (data.get("choices") or [{}])[0].get("message") or {}
        return ChatResult(
            content=message.get("content") or "",
            tool_calls=message.get("tool_calls") or [],
            usage=self._normalize_usage(data.get("usage") or {}),
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

    async def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        """批量向量化，返回与入参顺序一致的向量列表"""
        if not texts:
            return []
        payload = {"model": model or settings.AI_EMBEDDING_MODEL, "input": texts}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/embeddings",
                    headers=self._headers,
                    json=payload,
                )
                if response.status_code >= 400:
                    raise AIProviderError(
                        f"向量服务返回 {response.status_code}：{response.text[:300]}"
                    )
                data = response.json()
        except httpx.TimeoutException as exc:
            raise AIProviderError("向量服务响应超时") from exc
        except httpx.HTTPError as exc:
            raise AIProviderError(f"向量服务连接失败：{exc}") from exc

        items = sorted(data.get("data", []), key=lambda item: item.get("index", 0))
        return [item.get("embedding", []) for item in items]

    @staticmethod
    def _normalize_usage(usage: dict[str, Any]) -> dict[str, int]:
        """统一用量字段，便于计量与前端展示"""
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": int(usage.get("total_tokens") or prompt_tokens + completion_tokens),
        }


def get_chat_provider() -> OpenAICompatibleProvider:
    """获取对话模型客户端，未配置密钥时抛出业务异常"""
    if not settings.ai_configured:
        raise AIProviderError(
            "AI 功能还没有启用，请在项目配置文件中填写 AI 服务密钥后再试",
            ErrorCode.AI_NOT_CONFIGURED,
        )
    return OpenAICompatibleProvider(
        settings.AI_BASE_URL, settings.AI_API_KEY, settings.AI_REQUEST_TIMEOUT
    )


def get_embedding_provider() -> OpenAICompatibleProvider:
    """获取向量模型客户端，未配置时复用对话模型配置"""
    if not settings.embedding_api_key:
        raise AIProviderError(
            "AI 功能还没有启用，请在项目配置文件中填写 AI 服务密钥后再试",
            ErrorCode.AI_NOT_CONFIGURED,
        )
    return OpenAICompatibleProvider(
        settings.embedding_base_url, settings.embedding_api_key, settings.AI_REQUEST_TIMEOUT
    )

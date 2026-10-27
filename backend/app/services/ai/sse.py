"""SSE 事件编码：与前端约定的统一事件协议

事件类型：
- meta                 会话/模型等元信息
- token                增量文本
- citation             检索引用
- tool_call            Agent 发起工具调用
- tool_result          工具执行结果
- awaiting_confirmation 写操作等待用户确认
- done                 正常结束（携带用量与会话 ID）
- error                异常结束
"""

import json
from typing import Any


def sse_event(event: str, data: dict[str, Any]) -> str:
    """将事件编码为 SSE 帧"""
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


def sse_comment(text: str = "keep-alive") -> str:
    """SSE 注释帧，用于长任务保活"""
    return f": {text}\n\n"

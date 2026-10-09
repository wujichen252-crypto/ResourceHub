"""
响应序列化共享工具
- JSON 字符串列（tags/variables/values/labels）解码：兼容传入 JSON 字符串、None 或已解码容器
- HTML 剥离：与列表预览的现行行为保持一致
- 空值兜底：可空字符串列输出 "" 而非 null（与现行响应字节兼容）
"""
import json
import re
from typing import Any

from pydantic import BeforeValidator
from typing_extensions import Annotated


def decode_json_list(value: Any) -> list:
    """JSON 数组字符串 / None / 已是 list → list"""
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return json.loads(value)
    return value


def decode_json_dict(value: Any) -> dict:
    """JSON 对象字符串 / None / 已是 dict → dict"""
    if value is None or value == "":
        return {}
    if isinstance(value, str):
        return json.loads(value)
    return value


def none_to_empty(value: Any) -> Any:
    """None → ""（其余原样）"""
    return "" if value is None else value


def strip_html(text: str) -> str:
    """去除 HTML 标签，用于生成纯文本预览"""
    return re.sub(r"<[^>]+>", "", text)


# 可复用注解类型：响应模型中的 JSON 列与空串兜底字段直接引用
JsonList = Annotated[list, BeforeValidator(decode_json_list)]
JsonDict = Annotated[dict, BeforeValidator(decode_json_dict)]
EmptyStr = Annotated[str, BeforeValidator(none_to_empty)]

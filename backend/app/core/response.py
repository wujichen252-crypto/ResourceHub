"""
统一 API 响应格式封装
标准格式: { "code": 200, "data": any, "msg": "ok" }
"""

from typing import Any

from fastapi.responses import JSONResponse
from sqlalchemy import inspect
from sqlalchemy.orm import DeclarativeBase


def orm_to_dict(obj: DeclarativeBase) -> dict[str, Any]:
    """
    将 ORM 实例的列值转为 dict（只含列，不触碰 relationship，避免异步惰性加载）
    供路由层合并富化字段（如 category_name）后交给响应模型校验
    """
    return {
        column.key: getattr(obj, column.key)
        for column in inspect(obj).mapper.column_attrs
    }


def success_response(data: Any = None, msg: str = "ok", code: int = 200) -> dict:
    """
    构造成功响应

    Args:
        data: 响应数据
        msg: 响应消息
        code: 响应码，默认 200

    Returns:
        标准格式的响应字典
    """
    return {
        "code": code,
        "data": data,
        "msg": msg,
    }


def error_response(msg: str = "error", code: int = 400, data: Any = None) -> dict:
    """
    构造错误响应

    Args:
        msg: 错误消息
        code: 错误码，默认 400
        data: 附加数据

    Returns:
        标准格式的响应字典
    """
    return {
        "code": code,
        "data": data,
        "msg": msg,
    }


class APIError(Exception):
    """
    自定义 API 异常基类
    可被全局异常处理器捕获并转换为标准响应格式
    """

    def __init__(self, code: int, msg: str, data: Any = None):
        self.code = code
        self.msg = msg
        self.data = data
        super().__init__(msg)

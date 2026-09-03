"""
统一错误码定义

错误码规范:
- 200: 成功
- 4xx: 客户端错误
- 5xx: 服务端错误
- 1xxx: 业务错误（认证、授权等）
"""

from enum import IntEnum


class ErrorCode(IntEnum):
    """统一错误码枚举"""

    SUCCESS = 200

    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    VALIDATION_ERROR = 422

    INTERNAL_ERROR = 500

    USERNAME_EXISTS = 1001
    EMAIL_EXISTS = 1002
    INVALID_CREDENTIALS = 1003
    TOKEN_EXPIRED = 1004
    TOKEN_INVALID = 1005
    USER_NOT_FOUND = 1006

    NOTE_NOT_FOUND = 2001
    CATEGORY_NOT_FOUND = 3001
    PROMPT_NOT_FOUND = 4001


ERROR_MESSAGES = {
    ErrorCode.SUCCESS: "操作成功",
    ErrorCode.BAD_REQUEST: "请求参数错误",
    ErrorCode.UNAUTHORIZED: "未授权访问",
    ErrorCode.FORBIDDEN: "禁止访问",
    ErrorCode.NOT_FOUND: "资源不存在",
    ErrorCode.CONFLICT: "资源冲突",
    ErrorCode.VALIDATION_ERROR: "数据验证失败",
    ErrorCode.INTERNAL_ERROR: "服务器内部错误",
    ErrorCode.USERNAME_EXISTS: "用户名已被注册",
    ErrorCode.EMAIL_EXISTS: "邮箱已被注册",
    ErrorCode.INVALID_CREDENTIALS: "用户名或密码错误",
    ErrorCode.TOKEN_EXPIRED: "Token 已过期",
    ErrorCode.TOKEN_INVALID: "Token 无效",
    ErrorCode.USER_NOT_FOUND: "用户不存在",
    ErrorCode.NOTE_NOT_FOUND: "笔记不存在",
    ErrorCode.CATEGORY_NOT_FOUND: "分类不存在",
    ErrorCode.PROMPT_NOT_FOUND: "提示词不存在",
}


def get_error_message(code: int) -> str:
    """根据错误码获取错误消息"""
    return ERROR_MESSAGES.get(code, "未知错误")

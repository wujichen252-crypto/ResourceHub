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
    WRONG_OLD_PASSWORD = 1008

    RESET_CODE_INVALID = 1009
    RESET_CODE_EXPIRED = 1010
    RESET_CODE_ATTEMPTS_EXCEEDED = 1011
    EMAIL_NOT_CONFIGURED = 1012
    EMAIL_SEND_FAILED = 1013

    NOTE_NOT_FOUND = 2001
    CATEGORY_NOT_FOUND = 3001
    PROMPT_NOT_FOUND = 4001
    VERSION_NOT_FOUND = 4002
    PRESET_NOT_FOUND = 4003

    PLAZA_ITEM_NOT_FOUND = 5001
    INVALID_CONTENT_TYPE = 5002

    CANNOT_REACT_OWN_NOTE = 6001

    AI_NOT_CONFIGURED = 7001
    AI_PROVIDER_ERROR = 7002
    AI_QUOTA_EXCEEDED = 7003
    AI_CONTENT_BLOCKED = 7004
    AI_RUN_NOT_FOUND = 7005
    AI_CONFIRM_REQUIRED = 7006
    AGENT_PROFILE_NOT_FOUND = 7007
    MEMORY_NOT_FOUND = 7008
    MEMORY_LIMIT_EXCEEDED = 7009
    PROACTIVE_MESSAGE_NOT_FOUND = 7010

    TEAM_NOT_FOUND = 8001
    TEAM_FORBIDDEN = 8002
    TEAM_MEMBER_EXISTS = 8003
    TEAM_INVITE_INVALID = 8004
    TEAM_OWNER_CANNOT_LEAVE = 8005
    TEAM_MEMBER_NOT_FOUND = 8006


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
    ErrorCode.WRONG_OLD_PASSWORD: "原密码错误",
    ErrorCode.RESET_CODE_INVALID: "验证码无效或已过期",
    ErrorCode.RESET_CODE_EXPIRED: "验证码已过期，请重新获取",
    ErrorCode.RESET_CODE_ATTEMPTS_EXCEEDED: "验证码错误次数过多，请重新获取",
    ErrorCode.EMAIL_NOT_CONFIGURED: "邮件服务未配置，暂时无法发送验证码",
    ErrorCode.EMAIL_SEND_FAILED: "验证码发送失败，请稍后再试",
    ErrorCode.NOTE_NOT_FOUND: "笔记不存在",
    ErrorCode.CATEGORY_NOT_FOUND: "分类不存在",
    ErrorCode.PROMPT_NOT_FOUND: "提示词不存在",
    ErrorCode.VERSION_NOT_FOUND: "版本不存在",
    ErrorCode.PRESET_NOT_FOUND: "预设不存在",
    ErrorCode.PLAZA_ITEM_NOT_FOUND: "广场内容不存在或未发布",
    ErrorCode.INVALID_CONTENT_TYPE: "内容类型无效",
    ErrorCode.CANNOT_REACT_OWN_NOTE: "不能给自己的笔记点赞或收藏",
    ErrorCode.AI_NOT_CONFIGURED: "AI 功能还没有启用，请在项目配置文件中填写 AI 服务密钥后再试",
    ErrorCode.AI_PROVIDER_ERROR: "AI 服务暂时不可用，请稍后再试",
    ErrorCode.AI_QUOTA_EXCEEDED: "今天的 AI 使用次数已用完，请明天再试",
    ErrorCode.AI_CONTENT_BLOCKED: "内容未通过安全检查",
    ErrorCode.AI_RUN_NOT_FOUND: "Agent 运行记录不存在",
    ErrorCode.AI_CONFIRM_REQUIRED: "该操作需要用户确认后执行",
    ErrorCode.AGENT_PROFILE_NOT_FOUND: "智能体人格不存在",
    ErrorCode.MEMORY_NOT_FOUND: "记忆不存在",
    ErrorCode.MEMORY_LIMIT_EXCEEDED: "记忆数量已达上限，请先清理部分记忆",
    ErrorCode.PROACTIVE_MESSAGE_NOT_FOUND: "主动消息不存在",
    ErrorCode.TEAM_NOT_FOUND: "团队不存在",
    ErrorCode.TEAM_FORBIDDEN: "仅团队成员可以访问该资源",
    ErrorCode.TEAM_MEMBER_EXISTS: "你已经是该团队成员",
    ErrorCode.TEAM_INVITE_INVALID: "邀请码无效",
    ErrorCode.TEAM_OWNER_CANNOT_LEAVE: "团队创建者不能直接退出，请先删除团队",
    ErrorCode.TEAM_MEMBER_NOT_FOUND: "团队成员不存在",
}


def get_error_message(code: int) -> str:
    """根据错误码获取错误消息"""
    return ERROR_MESSAGES.get(code, "未知错误")

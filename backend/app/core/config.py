"""
ResourceHub 配置管理
从环境变量读取配置，支持 .env 文件
生产环境必须通过环境变量设置敏感配置
"""

import os
import secrets
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类"""

    APP_NAME: str = "ResourceHub"
    VERSION: str = "0.1.0"
    DEBUG: bool = True
    ENV: str = "development"

    DATABASE_URL: str = "sqlite+aiosqlite:///./resourcehub.db"

    SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:80"

    # ── AI 能力层配置（OpenAI 兼容协议，可切换 DeepSeek / 智谱 / 通义 / OpenAI）──
    AI_BASE_URL: str = "https://api.deepseek.com/v1"
    AI_API_KEY: str = ""
    AI_CHAT_MODEL: str = "deepseek-chat"
    AI_FAST_MODEL: str = "deepseek-chat"  # 摘要、打标、评测等轻量任务
    AI_EMBEDDING_BASE_URL: str = ""  # 留空则复用 AI_BASE_URL
    AI_EMBEDDING_API_KEY: str = ""  # 留空则复用 AI_API_KEY
    AI_EMBEDDING_MODEL: str = "embedding-3"
    AI_EMBEDDING_DIM: int = 2048  # 智谱 embedding-3 默认输出维度
    AI_EMBEDDING_BATCH_SIZE: int = 16
    AI_REQUEST_TIMEOUT: float = 60.0
    AI_MAX_OUTPUT_TOKENS: int = 2048
    AI_AGENT_MAX_STEPS: int = 6
    AI_DAILY_TOKEN_QUOTA: int = 500000  # 单用户每日 token 上限，防止演示额度被刷爆
    AI_CHUNK_SIZE: int = 700  # 分块目标字符数
    AI_CHUNK_OVERLAP: int = 100  # 相邻分块重叠字符数
    AI_RETRIEVAL_CANDIDATES: int = 4000  # 单次检索参与打分的 chunk 上限
    AI_MIN_VECTOR_SCORE: float = 0.5  # 低于该余弦相似度且无关键词命中时视为无依据，触发拒答

    model_config = SettingsConfigDict(
        # 无论从项目根目录还是 backend 目录启动，都读取项目根目录配置。
        env_file=Path(__file__).resolve().parents[3] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """将逗号分隔的字符串转换为列表"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._validate_secret_key()

    def _validate_secret_key(self) -> None:
        """
        验证 SECRET_KEY 配置
        生产环境不允许使用默认或空密钥
        """
        if not self.SECRET_KEY:
            if self.ENV == "production":
                raise ValueError(
                    "生产环境必须设置 SECRET_KEY 环境变量！"
                    "请生成一个强密钥并配置到环境变量中。"
                )
            self.SECRET_KEY = self._generate_dev_secret_key()
            print(
                f"[警告] 开发环境使用自动生成的 SECRET_KEY。"
                f"生产环境请务必设置 SECRET_KEY 环境变量！"
            )

    @staticmethod
    def _generate_dev_secret_key() -> str:
        """生成开发环境用的随机密钥"""
        return secrets.token_hex(32)

    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.ENV == "production"

    @property
    def ai_configured(self) -> bool:
        """是否已配置可用的对话模型密钥"""
        return bool(self.AI_API_KEY and self.AI_BASE_URL)

    @property
    def embedding_base_url(self) -> str:
        """向量模型服务地址，未单独配置时复用对话模型服务"""
        return self.AI_EMBEDDING_BASE_URL or self.AI_BASE_URL

    @property
    def embedding_api_key(self) -> str:
        """向量模型密钥，未单独配置时复用对话模型密钥"""
        return self.AI_EMBEDDING_API_KEY or self.AI_API_KEY


settings = Settings()

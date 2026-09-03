"""
ResourceHub 配置管理
从环境变量读取配置，支持 .env 文件
生产环境必须通过环境变量设置敏感配置
"""

import os
import secrets

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

    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:80"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

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


settings = Settings()

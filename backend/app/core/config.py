"""
ResourceHub 配置管理
从环境变量读取配置，支持 .env 文件
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "ResourceHub"
    VERSION: str = "0.1.0"
    DEBUG: bool = True

    # 数据库
    DATABASE_URL: str = "sqlite+aiosqlite:///./resourcehub.db"

    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120  # 2 小时
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7     # 7 天

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:80"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

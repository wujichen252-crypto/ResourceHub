FROM python:3.12-slim

WORKDIR /app

# 复制依赖文件
COPY pyproject.toml ./

# 安装依赖 - 直接从 pyproject.toml 提取
RUN pip install --no-cache-dir \
    fastapi==0.115.0 \
    uvicorn[standard]==0.30.0 \
    sqlalchemy[asyncio]==2.0.35 \
    aiosqlite==0.20.0 \
    aiomysql==0.2.0 \
    alembic==1.13.2 \
    pydantic==2.9.0 \
    pydantic-settings==2.5.0 \
    python-jose[cryptography]==3.3.0 \
    passlib[bcrypt]==1.7.4 \
    bcrypt==4.1.3 \
    python-multipart==0.0.12

# 复制源码
COPY . .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

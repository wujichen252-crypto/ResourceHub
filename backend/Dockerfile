FROM python:3.10-slim

WORKDIR /app

# ── 依赖安装：以 uv.lock 为唯一事实来源 ──
# 原实现手写 pip 清单，新增依赖时极易漏装（例如搜索适配层所需 httpx）。
# 改为按 uv.lock 冻结安装，与本地/CI 版本完全一致；--frozen 在锁文件与
# pyproject.toml 不一致时会直接失败，从而把依赖漂移挡在构建阶段。
RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

# 复制源码
COPY . .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# 数据库迁移快速参考

## 📊 迁移完成状态

✅ **数据库迁移已完成** (2026-09-20)

### 迁移统计
- 👤 用户: 4 个
- 📝 笔记: 20 篇
- 📁 分类: 61 个
- 🤖 提示词: 1 个
- 📦 版本记录: 1 条

## 🔧 当前配置

### 后端数据库配置 (`backend/.env`)
```
DATABASE_URL=mysql+aiomysql://resourcehub:km56iwexNjzyrGEd@162.14.111.9/resourcehub
```

### 验证连接
```bash
cd backend
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8800
```

预期输出中应包含:
```
INFO:     Application startup complete.
```

## 🚀 启动应用

### 后端
```bash
cd backend
uv sync              # 首次安装依赖
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8800
```

### 前端
```bash
cd frontend
npm install          # 首次安装依赖
npm run dev          # 启动开发服务器 (http://localhost:5173)
```

### 一键 Docker
```bash
docker compose up --build
```

## 📁 重要文件

| 文件 | 说明 |
|------|------|
| `backend/.env` | 数据库连接配置（已配置远程 MySQL）|
| `backend/migrate_to_remote.py` | 迁移脚本（如需重新迁移） |
| `MIGRATION_REPORT.md` | 详细迁移报告 |
| `resourcehub.db` | 本地 SQLite（已保留作备份） |

## ❓ 常见问题

### Q: 如何验证数据是否在远程数据库中？
```bash
cd backend
uv run python << 'EOF'
import asyncio
from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.user import User

async def check():
    async with SessionLocal() as session:
        users = await session.execute(select(User))
        print(f"用户数: {len(users.scalars().all())}")

asyncio.run(check())
EOF
```

### Q: 本地 SQLite 数据库需要删除吗？
**不需要**。本地 `resourcehub.db` 已保留作为备份。应用已配置使用远程 MySQL。

### Q: 如何重新迁移数据？
```bash
cd backend
uv run python migrate_to_remote.py
```
> ⚠️ 注意：此操作会清空远程数据库后重新迁移本地数据

### Q: 生产部署时如何配置数据库？
通过环境变量设置（不要提交 .env 文件）：
```bash
export DATABASE_URL="mysql+aiomysql://user:password@host:3306/resourcehub"
```

## 🔐 安全提示

- ✅ `.env` 文件已在 `.gitignore` 中，不会被提交
- ⚠️ 生产环境必须通过环境变量（不是 .env 文件）设置凭证
- 🔒 数据库密码不要在代码中硬编码

## 📞 需要帮助？

查看详细报告：[MIGRATION_REPORT.md](./MIGRATION_REPORT.md)


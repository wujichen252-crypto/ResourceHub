# ResourceHub 数据库迁移（SQLite → MySQL）

> 本文档由原根目录 4 份迁移文档（`MIGRATION_REPORT.md`、`MIGRATION_COMPLETE.md`、`MIGRATION_VERIFIED.md`、`DATABASE_MIGRATION_GUIDE.md`）合并归档而来，凭证信息已脱敏。

## 迁移记录

- **迁移时间**: 2026-09-20
- **迁移类型**: 本地 SQLite（`resourcehub.db`）→ 远程 MySQL 5.7
- **数据完整性**: 100%

| 表名 | 数据量 | 状态 |
|------|-------|------|
| users | 4 | ✅ |
| categories | 61 | ✅ |
| notes | 20 | ✅ |
| prompts | 1 | ✅ |
| prompt_versions | 1 | ✅ |
| prompt_presets / prompt_usage_logs | 0 | - |

### 迁移方式

- 脚本：`backend/migrate_to_remote.py`（异步批量迁移，自动清空、外键处理、数据验证）
- 步骤：清空远程库（禁用外键检查）→ SQLAlchemy metadata 建表 → 按依赖顺序迁移数据（User → Category → Note/Prompt）→ 计数与采样校验
- 字符集：utf8mb4（完整支持中文和 emoji）

> 注：迁移完成后数据库实例有过变更，当前生产连接以 `backend/.env` 的 `DATABASE_URL` 为准（见 AGENTS.md）。schema 变更现由 Alembic 迁移管辖（`backend/migrations/`）。

## 重新迁移操作指引

⚠️ 以下操作会**清空远程数据库**后重新迁移本地 SQLite 数据，仅在确认需要时使用：

```bash
cd backend
uv run python migrate_to_remote.py
```

前置条件：本地存在 `resourcehub.db` 备份文件，且 `backend/.env` 中 `DATABASE_URL` 指向目标库。

## 验证连接

```bash
cd backend
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8800
```

预期输出包含 `Application startup complete.`。

查询远程数据抽样验证：

```bash
cd backend
uv run python -c "
import asyncio
from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.user import User

async def check():
    async with SessionLocal() as session:
        users = await session.execute(select(User))
        print(f'用户数: {len(users.scalars().all())}')

asyncio.run(check())
"
```

## 生产部署配置

通过环境变量设置（不要提交 `.env` 文件）：

```bash
export DATABASE_URL="mysql+aiomysql://<user>:<password>@<host>:3306/resourcehub"
```

## 常见问题

| 问题 | 处理 |
|------|------|
| 远程 MySQL 连接失败 | 检查网络和防火墙；先测端口连通性 |
| 主键冲突 | 确保远程库已清空（`migrate_to_remote.py` 已自动处理） |
| 字符编码异常 | 确认库/表为 utf8mb4 |
| 本地 SQLite 是否删除 | 可选。保留作备份不影响运行 |

## 安全提示

- `.env` 已在 `.gitignore` 中，不会被提交
- 生产环境凭证必须通过环境变量注入，不要硬编码
- 历史文档中曾出现明文数据库密码，建议尽快在 MySQL 侧轮换该账号密码

# ResourceHub 项目文件清理与结构整理

## Context

项目经过多轮迭代（SQLite→MySQL 迁移、Docker 部署、多次功能开发），根目录积累了大量历史文档、临时备份、死代码和重复配置，结构松散。本次清理目标：删除冗余、归档历史、归位脚本，使目录简洁清晰且便于后续扩展。

用户已确认的决策：
1. 迁移历史文档 → 合并归档到 `docs/`
2. `backend.zip`、两张截图 → 全部删除
3. `_archive/` 旧组件、`backend/migrate.py` → 全部删除
4. 部署脚本 → 归入 `scripts/deploy/`，compose 统一保留根目录一份

## 现状盘点（已核实）

- 根目录杂物：`backend.zip`（20MB 未入库备份）、`rh_dashboard.png`、`rh_login.png`（已入库但全项目零引用）
- 迁移历史文档 4 份：`MIGRATION_COMPLETE.md`、`MIGRATION_REPORT.md`、`MIGRATION_VERIFIED.md`、`DATABASE_MIGRATION_GUIDE.md`（迁移 2026-09 已完成；schema 现由 alembic 管辖）
- 死代码：`backend/migrate.py`（面向已废弃的本地 `resourcehub.db`，该文件已不存在）；`frontend/src/views/Notes/_archive/`（NoteDetail/NoteEditor/NoteList 三个旧组件，Grep 确认零引用）
- 重复 compose：根目录 `docker-compose.yml`（生产版，`deploy-server.sh` 实际使用的就是它）与 `backend/docker-compose.yml`（开发期遗留，端口/网络命名均不一致）
- 部署脚本散落根目录：`deploy.sh`、`deploy-server.sh`、`deploy.ps1`、`deploy.config.example.ps1`、`webhook-deploy.py`
- `.gitignore` 缺 `.pytest_cache/`；`AGENTS.md` 的 Memory Bank 段落写的是 `Codex-*.md` 但实际文件为 `CLAUDE-*.md`
- `README.md` 仅 1 行标题

## 执行步骤

### 1. 删除冗余文件

- `backend.zip`
- `rh_dashboard.png`、`rh_login.png`（`git rm`）
- `backend/migrate.py`
- `frontend/src/views/Notes/_archive/` 整个目录（3 个 .vue 文件）
- `backend/docker-compose.yml`（保留根目录版为唯一 compose 入口；其开发用法已在 AGENTS.md 有 `uv run uvicorn` 替代）

> 保留 `backend/migrate_to_remote.py` —— `DATABASE_MIGRATION_GUIDE.md` 明确其为"如需重新迁移"的工具，仍有价值。

### 2. 归档迁移文档 → `docs/database-migration.md`

- 新建根目录 `docs/`（`backend/docs/` 为模块级文档，保持不动）
- 将 4 份迁移文档合并为一份 `docs/database-migration.md`：以 `DATABASE_MIGRATION_GUIDE.md` 的重迁操作指引为主体（含 `uv run python migrate_to_remote.py` 步骤与脚本清单），把 3 份报告类文档压缩为"迁移记录"一节（时间线、结论、验证要点），删除重复内容
- 删除原 4 份根目录文档（`git rm`）

### 3. 部署脚本归入 `scripts/deploy/`

移动（`git mv`）：`deploy.sh`、`deploy-server.sh`、`deploy.ps1`、`deploy.config.example.ps1`、`webhook-deploy.py` → `scripts/deploy/`

同步修正脚本内路径引用（关键，否则部署链路断裂）：
- `deploy-server.sh`：`cd "$(dirname "$0")"` 后会位于 `scripts/deploy/`，需改为 `cd "$(dirname "$0")/../.."`（回到仓库根），`docker compose` 与 `git` 命令才能按原语义工作
- `webhook-deploy.py`：`DEPLOY_SCRIPT = '/opt/ResourceHub/deploy.sh'` → `'/opt/ResourceHub/scripts/deploy/deploy.sh'`
- `deploy.ps1` / `deploy.sh`：检查内部相对路径（如 `deploy.config.local.ps1` 的引用位置），随脚本一起迁移配置示例文件并在脚本内更新路径
- `DEPLOYMENT_GUIDE.md`：更新其中 `/opt/ResourceHub/deploy.sh`、`webhook-deploy.py` 等路径描述
- 服务器端注意：`/opt/ResourceHub` 上的旧 `deploy.sh` 与 systemd/nohup 的 webhook 服务指向旧路径，首次部署后需按新路径重启 webhook（在最终交付说明中提醒用户，本仓库无法代改）

### 4. 配置与文档修正

- `.gitignore`：追加 `.pytest_cache/`
- `AGENTS.md`：
  - 架构树更新：新增 `scripts/deploy/`、`docs/`，移除已删文件，compose 只列根目录
  - Memory Bank 段落 `Codex-*.md` → `CLAUDE-*.md`（与实际文件对齐）
  - 命令段落如有 `docker compose` 相关说明保持根目录入口不变
- `README.md`：补齐最简项目说明（一句话简介、技术栈、目录结构、启动命令指引到 AGENTS.md），不展开成长文档

### 5. 验证

- `cd backend; uv run pytest -q` —— 48 个测试全绿
- `cd frontend; npm run build` —— 构建通过（确认删除 `_archive/` 无残留引用）
- `git status` 干净核对：无未跟踪杂物、删除均为预期文件
- Grep 复查全项目不再存在对已删文件/旧脚本路径的引用（`migrate.py`、`_archive`、`backend/docker-compose`、`MIGRATION_`、`/opt/ResourceHub/deploy.sh`）

## 不做的事

- 不移动 `backend/docs/`（模块级文档，路径稳定）
- 不动 `CLAUDE-*.md` 本地记忆文件（已被 gitignore，跨会话使用）
- 不动 `.trae/documents/`（计划文档目录）
- 不重命名任何在用模块/组件

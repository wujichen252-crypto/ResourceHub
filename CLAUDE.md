# CLAUDE.md — ResourceHub（资源整合中心）

<!-- Run /init to auto-populate interactive mode -->
<!-- Keep under 200 lines. If removing a line wouldn't cause mistakes, cut it -->

## Project Overview

- **Name:** ResourceHub（资源整合中心）
- **Stack:** Vue 3 + TypeScript / Python FastAPI / SQLAlchemy 2.0 / SQLite → PostgreSQL
- **Description:** 个人知识管理与 AI 提示词管理的一体化工具。面向开发者、AI 使用者、知识工作者，提供笔记整理 + AI 提示词库两大核心功能。
- **Entry:** `backend/main.py`（后端）/ `frontend/src/main.ts`（前端）

## Commands

```bash
# ── 后端 ──────────────────────────────────────────
cd backend

# 安装依赖
uv sync

# 启动开发服务（热重载）
uv run uvicorn main:app --reload --port 8000

# 运行测试
uv run pytest test_api.py -v

# 启动完整服务（Docker）
docker compose up --build

# ── 前端 ──────────────────────────────────────────
cd frontend

# 启动开发服务
npm run dev

# 构建生产版本
npm run build

# 预览构建结果
npm run preview
```

## Project Architecture

```
ResourceHub/
├── backend/                    # FastAPI 后端
│   ├── main.py                 # 应用入口，注册路由和中间件
│   ├── app/
│   │   ├── core/               # 基础设施
│   │   │   ├── config.py       # 配置管理（Pydantic Settings）
│   │   │   ├── database.py     # 数据库连接与会话
│   │   │   ├── deps.py         # FastAPI 依赖注入（认证、DB）
│   │   │   └── security.py     # JWT 令牌和密码哈希
│   │   ├── models/             # SQLAlchemy ORM 模型
│   │   │   ├── user.py         # 用户模型
│   │   │   ├── note.py         # 笔记模型（含全文本搜索）
│   │   │   ├── prompt.py       # 提示词模型（含变量字段）
│   │   │   └── category.py     # 分类模型（树形结构）
│   │   ├── schemas/            # Pydantic 请求/响应模式
│   │   ├── routers/            # API 路由
│   │   │   ├── auth.py         # 认证（注册/登录/刷新）
│   │   │   ├── notes.py        # 笔记 CRUD
│   │   │   ├── prompts.py      # 提示词 CRUD
│   │   │   └── categories.py   # 分类管理
│   ├── pyproject.toml        # uv 项目依赖声明
│   ├── uv.lock               # 锁定版本
│   └── Dockerfile
├── frontend/                   # Vue 3 + TypeScript 前端
│   ├── src/
│   │   ├── main.ts             # 应用入口
│   │   ├── App.vue             # 根组件
│   │   ├── router/index.ts     # 路由配置与导航守卫
│   │   ├── stores/             # Pinia 状态管理
│   │   ├── api/                # Axios HTTP 客户端
│   │   ├── views/              # 页面组件
│   │   │   ├── Login.vue
│   │   │   ├── Dashboard.vue
│   │   │   ├── Settings.vue
│   │   │   ├── Notes/          # 笔记模块页面
│   │   │   └── Prompts/        # 提示词模块页面
│   │   ├── components/         # 共享组件
│   │   └── styles/             # 全局样式
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
├── docker-compose.yml          # 全局编排
└── .gitignore
```

### 数据流

```
前端 (Vite:5173)  →  Axios  →  后端 (FastAPI:8000)  →  SQLAlchemy  →  SQLite/PostgreSQL
       ↑                              ↑
  Element Plus UI               JWT 认证中间件
  Pinia 状态管理                Pydantic 数据校验
```

---

## Rules

- **Investigate first:** Never speculate about code you have not read. Read files and `rg` for usages before making claims
- **Scope to the request:** Do what is asked; nothing more
- **Verify before done:** Re-check each requirement. Run tests and lint
- **File discipline:** Edit existing files in place. Do not create new files unless required
- **Safety:** Ask before destructive actions (deleting files/branches, force pushes)
- **Efficiency:** Parallelize independent tool calls; serialize dependent ones
- **Tools:** Use `rg` not grep, `fd` not find
- **i18n:** 代码注释和文档保持中文（项目面向中文用户）

---

## Memory Bank

This project uses CLAUDE-*.md files to retain context across sessions:

| File | Read When |
|------|-----------|
| `CLAUDE-activeContext.md` | Session start — current state and goals |
| `CLAUDE-patterns.md` | Before implementing — code patterns |
| `CLAUDE-decisions.md` | Before design choices — architecture ADRs |
| `CLAUDE-troubleshooting.md` | When debugging — known issues and fixes |

All optional — check existence first. Update after significant work.

## Context Layers

| Layer | Location | Loads | Survives Reset |
|-------|----------|-------|----------------|
| Core rules | This file | Always | No |
| Auto memory | `memory/MEMORY.md` | Always (first 200 lines) | Yes |
| Memory bank | CLAUDE-*.md | On demand | No — mirrored to auto memory |

# AGENTS.md — ResourceHub（资源整合中心）

<!-- Run /init to auto-populate interactive mode -->
<!-- Keep under 200 lines. If removing a line wouldn't cause mistakes, cut it -->

## Project Overview

- **Name:** ResourceHub（资源整合中心）
- **Stack:** Vue 3 + TypeScript / Python FastAPI / SQLAlchemy 2.0 / MySQL 5.7（远端 162.14.111.9；SQLite 已迁移，本地留档）
- **Description:** 个人知识管理与 AI 提示词管理的一体化工具。面向开发者、AI 使用者、知识工作者，提供笔记整理 + AI 提示词库两大核心功能。
- **Entry:** `backend/main.py`（后端）/ `frontend/src/main.ts`（前端）

## Commands

```bash
# ── 后端 ──────────────────────────────────────────
cd backend

# 安装依赖
uv sync

# 启动开发服务（热重载）
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8800

# 运行测试
uv run pytest -v

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
│   ├── docs/                 # 后端模块文档（API/架构/数据库设计）
│   ├── migrations/           # Alembic 迁移（生产 schema 管辖）
│   ├── tests/                # pytest 测试套件
│   └── Dockerfile
├── frontend/                   # Vue 3 + TypeScript 前端
│   ├── src/
│   │   ├── main.ts             # 应用入口（样式导入顺序：element-plus → theme.css → global.css → markdown.css）
│   │   ├── App.vue             # 根组件
│   │   ├── router/index.ts     # 路由配置与导航守卫（含 404 兜底路由）
│   │   ├── stores/             # Pinia 状态管理
│   │   ├── api/                # Axios HTTP 客户端
│   │   ├── composables/        # 组合式函数
│   │   │   ├── useChart.ts     # ECharts 按需引入封装（运行时读取 --rh-* 令牌）
│   │   │   └── useTheme.ts     # 主题单例（light/dark/system 三态）
│   │   ├── utils/format.ts     # 统一日期格式化（formatDate / formatDateTime / formatRelative）
│   │   ├── views/              # 页面组件
│   │   │   ├── Login.vue
│   │   │   ├── Dashboard.vue
│   │   │   ├── Settings.vue
│   │   │   ├── NotFound.vue    # 404 兜底页
│   │   │   ├── Notes/          # 笔记模块页面
│   │   │   ├── Prompts/        # 提示词模块页面
│   │   │   └── Plaza.vue       # 资源广场
│   │   ├── components/         # 共享组件
│   │   │   ├── common/         # EmptyState / LoadingState / ErrorState（全站统一状态组件）
│   │   │   ├── dashboard/      # VizCard（图表统一外壳）+ 4 个图表组件
│   │   │   ├── notes/          # NoteTree / NoteContent / NoteReader / WysiwygEditor
│   │   │   └── prompts/        # 版本历史 / 使用分析面板
│   │   └── styles/
│   │       ├── theme.css       # 设计令牌唯一事实来源（--rh-*，含浅色/深色两套）
│   │       ├── global.css      # 全局基础样式 + 工具类（.rh-page / .sr-only）
│   │       └── markdown.css    # Markdown 排版层（.rh-markdown，阅读态与广场详情共用）
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
├── scripts/deploy/             # 部署脚本（deploy.sh / deploy.ps1 / webhook-deploy.py 等）
├── docs/                       # 项目级归档文档（数据库迁移等）
├── docker-compose.yml          # 全局编排（唯一 compose 入口）
├── DEPLOYMENT_GUIDE.md         # 部署指南
└── .gitignore
```

### 数据流

```
前端 (Vite:5173)  →  Axios  →  后端 (FastAPI:8800)  →  SQLAlchemy(aiomysql)  →  MySQL 5.7 (162.14.111.9/resourcehub)
       ↑                              ↑
  Element Plus UI               JWT 认证中间件
  Pinia 状态管理                Pydantic 数据校验
```

---

## 前端设计规范（Frontend Design Conventions）

> 本节为 2026-10 UI 设计审查后的**规范对齐结论**，替代早期口头规范中「Tailwind CSS + 黑白极简（#000/#FFF/#F5F5F5 + #2563EB）」的表述。彼时描述与本项目实际实现不符，经确认以**实际实现为准**，规范向实现对齐（详见 `docs/ui-design-audit.md` 第八节 P2 #33）。

- **样式技术栈：** 不使用 Tailwind。样式方案为 **CSS 自定义属性设计令牌 + 组件内 `<style scoped>` + Element Plus**，令牌是唯一事实来源
- **令牌命名空间：** 全部为 `--rh-*`，定义在 `frontend/src/styles/theme.css`；浅色写在 `:root`，深色写在 `[data-theme="dark"]`
- **配色语言：** 暖调米白 + 赭红主色（`--rh-bg-base: #f5f3ee`、`--rh-primary: #b03c22`；深色 `#181a18` / `#ff765c`）。**禁止硬编码色值**，一律引用令牌；新语义色需先在 theme.css 定义
- **Element Plus 覆盖：** 用 `:root .el-xxx` 提升选择器特异性（(0,2,0) > Element Plus 的 (0,1,0)），**禁止 `!important`**；唯一例外是 `prefers-reduced-motion` 的动画时长压制
- **圆角只有三档：** `--rh-radius-xs: 3px` / `--rh-radius-sm: 5px` / `--rh-radius-md: 8px`。不新增档位，`999px`/`50%` 仅用于胶囊与圆形
- **层级用令牌：** `--rh-z-nav: 100` / `--rh-z-menu: 109` / `--rh-z-topbar: 110` / `--rh-z-popover: 200`。组件内部 sticky 层叠可用局部小值（如 10）
- **页面外壳：** 根容器加 `.rh-page`（列表型，1320px）或 `.rh-page rh-page--narrow`（详情/编辑/设置型，1000px）；**不要在页面 scoped 样式里重复写 `padding`/`max-width`/`margin: 0 auto`**（scoped 带 `[data-v-*]`，特异性会压过工具类）
- **状态呈现：** 空态用 `components/common/EmptyState.vue`，加载用 `LoadingState.vue`（骨架屏，禁止转圈图标），失败用 `ErrorState.vue`。禁止再各页自写 `.empty-state` / `.center-state`
- **Markdown 排版：** 统一走 `styles/markdown.css` 的 `.rh-markdown` 全局样式，容器加该类即可；禁止在组件内重复写 Markdown 排版规则
- **日期展示：** 统一用 `utils/format.ts` 的 `formatDate` / `formatDateTime` / `formatRelative`，禁止再用 `toLocaleString` 或手拼字符串
- **主题：** 通过 `composables/useTheme.ts` 单例管理（light / dark / system），入口在 NavBar 与 Settings；不要各组件自读 `localStorage`
- **过渡动画：** 用 `--rh-transition-all-*` 或显式列举属性，**禁止 `transition: all`**
- **焦点可见性：** 全站 `:focus-visible` 由 theme.css 统一提供；**禁止 `outline: none`**，需要自定义焦点样式时用 `:focus-within` + `--rh-focus-ring`
- **可访问性底线：** 图标按钮必须有 `aria-label`；右键菜单必须配「⋯」等价入口；破坏性操作确认框用 `type: 'error'`；图表需带无障碍数据表

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

# CLAUDE.md

<!-- Run /init to auto-populate interactive mode -->
<!-- Keep under 200 lines. If removing a line wouldn't cause mistakes, cut it -->

## Project Overview

- **Name:** ResourceHub Frontend · 资源整合中心前端
- **Stack:** Vue 3 + TypeScript + Vite + Pinia + Element Plus
- **Description:** 个人知识管理与 AI 提示词管理的一体化工具前端。支持笔记全流程管理（Markdown 编辑器、分类标签、全文搜索）、AI Prompt 模板管理（变量插值、一键复制、用量统计）、JWT 认证、数据导出
- **Entry:** `src/main.ts`

## Commands

```bash
# 开发启动
npm run dev                  # 启动 Vite 开发服务器 (localhost:5173)

# 构建
npm run build                # vue-tsc 类型检查 + Vite 生产构建

# 预览
npm run preview              # 预览生产构建

# 容器化构建
docker build -t resourcehub-frontend -f Dockerfile .
```

## Project Architecture

### 目录结构

```
frontend/
├── src/
│   ├── api/                  # Axios HTTP 请求封装
│   │   ├── http.ts           #   Axios 实例、拦截器（JWT 注入/刷新）
│   │   ├── auth.ts           #   认证 API
│   │   ├── notes.ts          #   笔记 API
│   │   ├── prompts.ts        #   提示词 API
│   │   └── categories.ts     #   分类 API
│   ├── components/           # 公共组件
│   │   └── NavBar.vue        #   顶部导航栏
│   ├── router/               # Vue Router 配置
│   │   └── index.ts          #   路由表 + 导航守卫
│   ├── stores/               # Pinia 状态管理
│   │   ├── auth.ts           #   认证状态（登录/注册/令牌刷新）
│   │   ├── notes.ts          #   笔记状态
│   │   ├── prompts.ts        #   提示词状态
│   │   └── categories.ts     #   分类状态
│   ├── views/                # 页面视图
│   │   ├── Login.vue         #   登录页
│   │   ├── Dashboard.vue     #   仪表盘
│   │   ├── Notes/            #   笔记模块（列表、详情、编辑器）
│   │   ├── Prompts/          #   提示词模块（列表、详情、编辑器）
│   │   └── Settings.vue      #   设置页
│   ├── styles/               # 全局样式
│   │   ├── global.css        #   全局样式
│   │   └── theme.css         #   主题变量
│   ├── App.vue               # 根组件
│   └── main.ts               # 入口文件
├── Dockerfile
├── nginx.conf
├── index.html
├── vite.config.ts
├── tsconfig.json
└── package.json
```

### 关键数据流

```
用户操作 → Vue 视图 → Pinia Store → Axios API → FastAPI Backend → SQLite/PostgreSQL
                                              ↕
                                        JWT Token (localStorage)
```

### 路由设计

| 路径 | 视图 | 需认证 |
|------|------|--------|
| `/login` | Login | 否（已登录自动跳转 Dashboard） |
| `/dashboard` | Dashboard | 是 |
| `/notes` | NoteList | 是 |
| `/notes/:id` | NoteDetail | 是 |
| `/notes/:id/edit` | NoteEditor | 是 |
| `/prompts` | PromptList | 是 |
| `/prompts/:id` | PromptDetail | 是 |
| `/prompts/:id/edit` | PromptEditor | 是 |
| `/settings` | Settings | 是 |

### API 代理

Vite 开发服务器配置 `/api` 代理到 `http://localhost:8000`，生产环境通过 Nginx 反代。

---

## Rules

- **Investigate first:** Never speculate about code you have not read. Read files and `rg` for usages before making claims
- **Scope to the request:** Do what is asked; nothing more
- **Verify before done:** Re-check each requirement. Run tests and lint
- **File discipline:** Edit existing files in place. Do not create new files unless required
- **Safety:** Ask before destructive actions (deleting files/branches, force pushes)
- **Efficiency:** Parallelize independent tool calls; serialize dependent ones
- **Tools:** Use `rg` not grep, `fd` not find
- **Vue 3 Composition API:** All components use `<script setup lang="ts">` syntax; avoid Options API
- **TypeScript strict mode:** Enabled; avoid `any` unless absolutely necessary
- **Pinia composition stores:** Use setup-function style (`defineStore('x', () => {...})`)
- **Element Plus:** Use El-* components for UI consistency; customize via CSS variables
- **Path alias:** `@/*` maps to `src/*`

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

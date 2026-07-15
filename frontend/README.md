<p align="center">
  <img src="https://img.shields.io/badge/Status-Development-blue?style=for-the-badge" alt="Status">
  <img src="https://img.shields.io/badge/Vue_3-4FC08D?style=for-the-badge&logo=vuedotjs&logoColor=white" alt="Vue 3">
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?style=for-the-badge&logo=python&logoColor=white" alt="SQLAlchemy">
  <img src="https://img.shields.io/badge/Element_Plus-409EFF?style=for-the-badge&logo=element&logoColor=white" alt="Element Plus">
</p>

<h1 align="center">📚 ResourceHub · 资源整合中心</h1>

<p align="center">
  <strong>个人知识管理与 AI 提示词管理的一体化工具</strong><br>
  <em>Your all-in-one hub for notes, knowledge, and AI prompts</em>
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-tech-stack">Tech Stack</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-project-structure">Structure</a> •
  <a href="#-api-overview">API</a> •
  <a href="#-development-roadmap">Roadmap</a>
</p>

---

## ✨ Features

<table>
  <tr>
    <td width="50%">
      <h3>📝 Note Management</h3>
      <ul>
        <li>✅ Full CRUD — Create, edit, delete, and view notes</li>
        <li>✅ Multi-level categories & tag system</li>
        <li>✅ Full-text search across titles and content</li>
        <li>✅ Markdown editor with live preview</li>
        <li>✅ Note linking & pinning</li>
      </ul>
    </td>
    <td width="50%">
      <h3>🤖 AI Prompt Library</h3>
      <ul>
        <li>✅ Full CRUD — Manage prompt templates</li>
        <li>✅ <code>{"{{variable}}"}</code> placeholder syntax</li>
        <li>✅ One-click copy to clipboard</li>
        <li>✅ Variable fill & rendered preview</li>
        <li>✅ Favorites, usage stats & categorization</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>🔐 User System</h3>
      <ul>
        <li>✅ JWT-based authentication</li>
        <li>✅ Register / Login / Token refresh</li>
        <li>✅ Route guards & persistent sessions</li>
      </ul>
    </td>
    <td width="50%">
      <h3>📦 Data Portability</h3>
      <ul>
        <li>✅ Export notes & prompts as JSON</li>
        <li>✅ Export notes as Markdown</li>
        <li>✅ Responsive design (PC + Mobile)</li>
      </ul>
    </td>
  </tr>
</table>

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────┐
│                   Client (Browser)               │
│  ┌───────────────────────────────────────────┐  │
│  │         Vue 3 + TypeScript + Pinia        │  │
│  │  ┌──────┐ ┌──────┐ ┌────────┐ ┌──────┐  │  │
│  │  │Auth  │ │Notes │ │Prompts │ │Dashboard│  │  │
│  │  │Views │ │Views │ │Views   │ │View    │  │  │
│  │  └──┬───┘ └──┬───┘ └───┬────┘ └───┬────┘  │  │
│  │     └────────┼──────────┼──────────┘       │  │
│  │         ┌────┴──────────┴────┐             │  │
│  │         │  API Layer (axios) │             │  │
│  │         └────────┬───────────┘             │  │
│  └──────────────────┼────────────────────────┘  │
└─────────────────────┼───────────────────────────┘
                      │ HTTP / JSON (JWT Auth)
┌─────────────────────┼───────────────────────────┐
│           FastAPI Backend (Python)               │
│  ┌──────────────────┴───────────┐               │
│  │         Routers             │               │
│  │  ┌──────┐ ┌──────┐ ┌──────┐│               │
│  │  │Auth  │ │Notes │ │Prompts││               │
│  │  └──┬───┘ └──┬───┘ └───┬──┘│               │
│  └─────┼────────┼──────────┼───┘               │
│  ┌─────┼────────┼──────────┼───────────────────┐│
│  │     │Services│          │                    ││
│  │  ┌──┴────────┴──────────┴──┐                ││
│  │  │      SQLAlchemy ORM     │                ││
│  │  └───────────┬─────────────┘                ││
│  └──────────────┼──────────────────────────────┘│
│                 │                               │
│        ┌────────┴────────┐                      │
│        │  SQLite / PG    │                      │
│        └─────────────────┘                      │
└─────────────────────────────────────────────────┘
```

---

## 🛠 Tech Stack

| Layer           | Technology                              |
| --------------- | --------------------------------------- |
| **Frontend**    | Vue 3 + TypeScript + Vite + Pinia       |
| **UI Library**  | Element Plus                            |
| **Backend**     | Python FastAPI                          |
| **Database**    | SQLite (dev) / PostgreSQL (production)  |
| **ORM**         | SQLAlchemy 2.0                          |
| **Auth**        | JWT (python-jose / PyJWT)               |
| **Deployment**  | Docker + Nginx                          |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Docker (optional, for production)

### Backend

```bash
# 1. Navigate to backend
cd backend

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate   # Linux/Mac
# venv\Scripts\activate    # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run database migrations
alembic upgrade head

# 5. Start dev server
uvicorn main:app --reload --port 8000
```

The API docs are now available at `http://localhost:8000/docs` ✨

### Frontend

```bash
# 1. Navigate to frontend
cd frontend

# 2. Install dependencies
npm install

# 3. Start dev server
npm run dev
```

The app will be available at `http://localhost:5173` 🎉

### Production (Docker)

```bash
docker-compose up -d
```

---

## 📁 Project Structure

```
resource-hub/
├── frontend/                     # Vue 3 前端
│   ├── src/
│   │   ├── api/                  # API 请求封装 (axios)
│   │   ├── components/           # 公共组件
│   │   ├── views/                # 页面视图
│   │   │   ├── Login.vue
│   │   │   ├── Dashboard.vue
│   │   │   ├── Notes/            # 笔记模块页面
│   │   │   └── Prompts/          # 提示词模块页面
│   │   ├── stores/               # Pinia 状态管理
│   │   ├── router/               # 路由配置
│   │   └── utils/                # 工具函数
│   ├── package.json
│   └── vite.config.ts
├── backend/                      # FastAPI 后端
│   ├── app/
│   │   ├── models/               # SQLAlchemy 数据模型
│   │   ├── routers/              # API 路由
│   │   ├── services/             # 业务逻辑层
│   │   ├── schemas/              # Pydantic 数据校验
│   │   └── core/                 # 配置、数据库、安全
│   ├── requirements.txt
│   └── main.py                   # 入口文件
├── docs/                         # 项目文档
│   ├── 数据库设计.md
│   ├── API接口文档.md
│   └── 开发计划与路线图.md
├── docker-compose.yml
├── 项目开发文档.md
├── ARCHITECTURE.md
└── README.md
```

---

## 📋 API Overview

| Module  | Method | Endpoint                     | Description              |
| ------- | ------ | ---------------------------- | ------------------------ |
| Auth    | POST   | `/api/auth/register`         | Register new user        |
| Auth    | POST   | `/api/auth/login`            | Login, returns JWT       |
| Auth    | POST   | `/api/auth/refresh`          | Refresh token            |
| Auth    | GET    | `/api/auth/me`               | Current user info        |
| Notes   | GET    | `/api/notes`                 | List notes (paginated)   |
| Notes   | POST   | `/api/notes`                 | Create note              |
| Notes   | GET    | `/api/notes/:id`             | Get note detail          |
| Notes   | PUT    | `/api/notes/:id`             | Update note              |
| Notes   | DELETE | `/api/notes/:id`             | Delete note              |
| Notes   | PUT    | `/api/notes/:id/pin`         | Toggle pin               |
| Prompts | GET    | `/api/prompts`               | List prompts             |
| Prompts | POST   | `/api/prompts`               | Create prompt            |
| Prompts | GET    | `/api/prompts/:id`           | Get prompt detail        |
| Prompts | PUT    | `/api/prompts/:id`           | Update prompt            |
| Prompts | DELETE | `/api/prompts/:id`           | Delete prompt            |
| Prompts | POST   | `/api/prompts/:id/render`    | Render with variables    |
| Prompts | POST   | `/api/prompts/:id/use`       | Increment usage count    |
| Prompts | PUT    | `/api/prompts/:id/favorite`  | Toggle favorite          |
| Cats    | GET    | `/api/categories?type=note`  | Get category tree        |
| Cats    | POST   | `/api/categories`            | Create category          |
| Cats    | PUT    | `/api/categories/:id`        | Update category          |
| Cats    | DELETE | `/api/categories/:id`        | Delete category          |

> 📖 Full API documentation is available in [docs/API接口文档.md](docs/API接口文档.md) or at `http://localhost:8000/docs` when the backend is running.

---

## 🗺 Development Roadmap

| Phase | Duration | Focus                                    |
| ----: | :------- | :--------------------------------------- |
| 1     | 3-4 days | Project skeleton, auth, database models   |
| 2     | 3-4 days | Notes module (CRUD, categories, search)   |
| 3     | 3-4 days | Prompts module (CRUD, variables, render)  |
| 4     | 2-3 days | UI polish, responsive, export, deployment |

See [docs/开发计划与路线图.md](docs/开发计划与路线图.md) for the full plan.

---

## 📄 License

MIT © ResourceHub

---

<p align="center"><em>Built with ❤️ for developers, AI users, and knowledge workers</em></p>

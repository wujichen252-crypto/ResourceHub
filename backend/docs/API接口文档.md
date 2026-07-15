# 🌐 ResourceHub API 接口文档

> **版本：** v1.0  
> **基础 URL：** `http://localhost:8000`  
> **认证方式：** JWT Bearer Token  
> **协议格式：** JSON over HTTP  
> **最后更新：** 2026-07-01

---

## 目录

1. [通用约定](#1-通用约定)
2. [认证模块](#2-认证模块-api-auth)
3. [笔记模块](#3-笔记模块-api-notes)
4. [提示词模块](#4-提示词模块-api-prompts)
5. [分类模块](#5-分类模块-api-categories)

---

## 1. 通用约定

### 1.1 请求头

```http
Content-Type: application/json
Authorization: Bearer <access_token>   # 认证接口除外
```

### 1.2 通用响应格式

**成功响应：**
```json
{
  "data": { ... },
  "message": "success"
}
```

**分页响应：**
```json
{
  "data": [ ... ],
  "total": 100,
  "page": 1,
  "page_size": 20
}
```

**错误响应：**
```json
{
  "detail": {
    "code": 401,
    "message": "认证失败，请重新登录",
    "errors": []
  }
}
```

### 1.3 HTTP 状态码

| 状态码 | 说明             | 使用场景             |
| ------ | ---------------- | -------------------- |
| 200    | OK               | 获取/更新成功        |
| 201    | Created          | 创建资源成功         |
| 204    | No Content       | 删除成功             |
| 400    | Bad Request      | 请求参数校验失败     |
| 401    | Unauthorized     | Token 无效或过期     |
| 403    | Forbidden        | 无权访问该资源       |
| 404    | Not Found        | 资源不存在           |
| 409    | Conflict         | 资源冲突（如用户名已存在）|
| 422    | Unprocessable    | Pydantic 校验失败    |
| 500    | Internal Error   | 服务器内部错误       |

### 1.4 API 概览

```
/api/auth/*          - 认证模块（无需认证）
/api/notes/*         - 笔记模块（需认证）
/api/prompts/*       - 提示词模块（需认证）
/api/categories/*    - 分类模块（需认证）
```

---

## 2. 认证模块 `/api/auth`

### 2.1 用户注册 `POST /api/auth/register`

注册新用户。

**请求体：**
```json
{
  "username": "alice",
  "password": "SecurePass123!",
  "email": "alice@example.com"
}
```

| 字段     | 类型   | 必填 | 约束             |
| -------- | ------ | ---- | ---------------- |
| username | string | 是   | 3-50 位字母/数字/下划线 |
| password | string | 是   | 8-128 位         |
| email    | string | 否   | 合法邮箱格式     |

**成功响应 `201 Created`：**
```json
{
  "data": {
    "id": 1,
    "username": "alice",
    "email": "alice@example.com",
    "created_at": "2026-07-01T10:00:00Z"
  }
}
```

**错误响应：**
```json
// 409 - 用户名已存在
{ "detail": { "code": 409, "message": "用户名 'alice' 已被注册" } }
```

---

### 2.2 用户登录 `POST /api/auth/login`

使用用户名和密码登录，获取 JWT Token。

**请求体：**
```json
{
  "username": "alice",
  "password": "SecurePass123!"
}
```

**成功响应 `200 OK`：**
```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 7200
  }
}
```

**Token 说明：**

| Token 类型    | 有效期 | 用途                       |
| ------------- | ------ | -------------------------- |
| access_token  | 2 小时 | 访问受保护的 API 资源       |
| refresh_token | 7 天   | 获取新的 access_token       |

**错误响应：**
```json
// 401 - 认证失败
{ "detail": { "code": 401, "message": "用户名或密码错误" } }
```

---

### 2.3 刷新 Token `POST /api/auth/refresh`

使用 refresh_token 获取新的 Token 对。

**请求体：**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**成功响应 `200 OK`：**
```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer"
  }
}
```

**错误响应：**
```json
// 401 - Refresh Token 无效或过期
{ "detail": { "code": 401, "message": "Token 已过期，请重新登录" } }
```

---

### 2.4 获取当前用户 `GET /api/auth/me`

获取当前认证用户的信息。

**请求头：**
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

**成功响应 `200 OK`：**
```json
{
  "data": {
    "id": 1,
    "username": "alice",
    "email": "alice@example.com",
    "avatar": null,
    "created_at": "2026-07-01T10:00:00Z"
  }
}
```

---

## 3. 笔记模块 `/api/notes`

### 3.1 获取笔记列表 `GET /api/notes`

获取当前用户的笔记列表，支持分页、搜索、分类筛选。

**查询参数：**

| 参数        | 类型    | 默认值 | 说明                              |
| ----------- | ------- | ------ | --------------------------------- |
| page        | integer | 1      | 页码                              |
| page_size   | integer | 20     | 每页条数（最大 100）              |
| search      | string  | -      | 全文搜索关键词                    |
| category_id | integer | -      | 按分类筛选                        |
| tag         | string  | -      | 按标签筛选                        |
| is_pinned   | boolean | -      | 只显示置顶笔记                    |

**请求示例：**
```http
GET /api/notes?page=1&page_size=10&search=vue&category_id=2
```

**成功响应 `200 OK`：**
```json
{
  "data": [
    {
      "id": 1,
      "title": "Vue 3 组合式 API 笔记",
      "content_preview": "Vue 3 引入了 Composition API...",
      "category_id": 2,
      "category_name": "前端",
      "tags": ["vue", "javascript", "frontend"],
      "is_pinned": true,
      "created_at": "2026-06-28T14:30:00Z",
      "updated_at": "2026-07-01T09:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 10
}
```

---

### 3.2 获取笔记详情 `GET /api/notes/:id`

**路径参数：**

| 参数 | 类型    | 说明   |
| ---- | ------- | ------ |
| id   | integer | 笔记 ID |

**成功响应 `200 OK`：**
```json
{
  "data": {
    "id": 1,
    "title": "Vue 3 组合式 API 笔记",
    "content": "Vue 3 引入了 Composition API，主要包含...（完整 Markdown 内容）",
    "category_id": 2,
    "category_name": "前端",
    "tags": ["vue", "javascript", "frontend"],
    "is_pinned": true,
    "created_at": "2026-06-28T14:30:00Z",
    "updated_at": "2026-07-01T09:00:00Z"
  }
}
```

**错误响应：**
```json
// 404 - 笔记不存在
{ "detail": { "code": 404, "message": "笔记不存在" } }

// 403 - 无权访问
{ "detail": { "code": 403, "message": "无权访问该笔记" } }
```

---

### 3.3 创建笔记 `POST /api/notes`

**请求体：**
```json
{
  "title": "FastAPI 入门指南",
  "content": "# FastAPI 入门\n\nFastAPI 是一个现代 Web 框架...",
  "category_id": 3,
  "tags": ["python", "fastapi", "backend"]
}
```

| 字段        | 类型   | 必填 | 说明             |
| ----------- | ------ | ---- | ---------------- |
| title       | string | 是   | 1-255 字符       |
| content     | string | 否   | Markdown 格式    |
| category_id | integer| 否   | 分类 ID          |
| tags        | array  | 否   | 字符串数组       |

**成功响应 `201 Created`：**
```json
{
  "data": {
    "id": 2,
    "title": "FastAPI 入门指南",
    "content": "# FastAPI 入门\n\nFastAPI 是一个现代 Web 框架...",
    "category_id": 3,
    "tags": ["python", "fastapi", "backend"],
    "is_pinned": false,
    "created_at": "2026-07-01T10:30:00Z",
    "updated_at": "2026-07-01T10:30:00Z"
  }
}
```

---

### 3.4 更新笔记 `PUT /api/notes/:id`

**请求体（部分更新）：**
```json
{
  "title": "FastAPI 完全指南",
  "tags": ["python", "fastapi", "backend", "api"]
}
```

**成功响应 `200 OK`：**
```json
{
  "data": {
    "id": 2,
    "title": "FastAPI 完全指南",
    "content": "# FastAPI 入门\n\nFastAPI 是一个现代 Web 框架...",
    "category_id": 3,
    "tags": ["python", "fastapi", "backend", "api"],
    "is_pinned": false,
    "created_at": "2026-07-01T10:30:00Z",
    "updated_at": "2026-07-01T11:00:00Z"
  }
}
```

---

### 3.5 删除笔记 `DELETE /api/notes/:id`

**成功响应 `204 No Content`**（无响应体）

---

### 3.6 置顶/取消置顶 `PUT /api/notes/:id/pin`

切换笔记的置顶状态。

**成功响应 `200 OK`：**
```json
{
  "data": {
    "id": 1,
    "is_pinned": true
  }
}
```

---

## 4. 提示词模块 `/api/prompts`

### 4.1 获取提示词列表 `GET /api/prompts`

**查询参数：**

| 参数         | 类型    | 默认值 | 说明              |
| ------------ | ------- | ------ | ----------------- |
| page         | integer | 1      | 页码              |
| page_size    | integer | 20     | 每页条数          |
| category_id  | integer | -      | 按分类筛选        |
| is_favorite  | boolean | -      | 只显示收藏        |
| search       | string  | -      | 按标题/描述搜索   |
| sort_by      | string  | created_at | 排序字段: usage_count / created_at |

**成功响应 `200 OK`：**
```json
{
  "data": [
    {
      "id": 1,
      "title": "代码审查助手",
      "description": "让 AI 以资深工程师视角审查代码",
      "category_id": 5,
      "category_name": "编程",
      "variables": ["language", "focus_areas", "code"],
      "is_favorite": true,
      "usage_count": 42,
      "created_at": "2026-06-15T10:00:00Z",
      "updated_at": "2026-07-01T08:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

---

### 4.2 获取提示词详情 `GET /api/prompts/:id`

**成功响应 `200 OK`：**
```json
{
  "data": {
    "id": 1,
    "title": "代码审查助手",
    "description": "让 AI 以资深工程师视角审查代码",
    "content": "请以资深软件工程师的身份，对以下 {{language}} 代码进行审查。\n关注点：{{focus_areas}}\n\n代码：\n```{{language}}\n{{code}}\n```",
    "category_id": 5,
    "category_name": "编程",
    "variables": ["language", "focus_areas", "code"],
    "is_favorite": true,
    "usage_count": 42,
    "created_at": "2026-06-15T10:00:00Z",
    "updated_at": "2026-07-01T08:00:00Z"
  }
}
```

---

### 4.3 创建提示词 `POST /api/prompts`

**请求体：**
```json
{
  "title": "代码审查助手",
  "description": "让 AI 以资深工程师视角审查代码",
  "content": "请以资深软件工程师的身份，对以下 {{language}} 代码进行审查。\n关注点：{{focus_areas}}\n\n代码：\n```{{language}}\n{{code}}\n```",
  "category_id": 5,
  "variables": ["language", "focus_areas", "code"]
}
```

| 字段        | 类型   | 必填 | 说明                           |
| ----------- | ------ | ---- | ------------------------------ |
| title       | string | 是   | 1-255 字符                     |
| description | string | 否   | 简短描述                       |
| content     | string | 是   | 提示词模板，可含 `{{变量}}`    |
| category_id | integer| 否   | 分类 ID                        |
| variables   | array  | 否   | 变量名列表，需与模板中的占位符对应 |

**成功响应 `201 Created`：**
```json
{
  "data": {
    "id": 1,
    "title": "代码审查助手",
    "description": "让 AI 以资深工程师视角审查代码",
    "content": "请以资深软件工程师的身份...",
    "category_id": 5,
    "variables": ["language", "focus_areas", "code"],
    "is_favorite": false,
    "usage_count": 0,
    "created_at": "2026-07-01T12:00:00Z"
  }
}
```

---

### 4.4 更新提示词 `PUT /api/prompts/:id`

**请求体（部分更新）：**
```json
{
  "title": "AI 代码审查助手 v2",
  "is_favorite": true
}
```

**成功响应 `200 OK`：**
```json
{
  "data": {
    "id": 1,
    "title": "AI 代码审查助手 v2",
    "is_favorite": true,
    "updated_at": "2026-07-01T12:30:00Z"
  }
}
```

---

### 4.5 删除提示词 `DELETE /api/prompts/:id`

**成功响应 `204 No Content`**

---

### 4.6 渲染提示词 `POST /api/prompts/:id/render`

传入变量值，渲染最终的提示词文本。

**请求体：**
```json
{
  "variables": {
    "language": "Python",
    "focus_areas": "性能优化, 安全性",
    "code": "def foo():\n    return 1"
  }
}
```

**成功响应 `200 OK`：**
```json
{
  "data": {
    "id": 1,
    "title": "代码审查助手",
    "original_content": "请以资深软件工程师的身份...",
    "rendered_content": "请以资深软件工程师的身份，对以下 Python 代码进行审查。\n关注点：性能优化, 安全性\n\n代码：\n```Python\ndef foo():\n    return 1\n```",
    "variables": {
      "language": "Python",
      "focus_areas": "性能优化, 安全性",
      "code": "def foo():\n    return 1"
    }
  }
}
```

**错误响应：**
```json
// 422 - 缺少必要变量
{
  "detail": {
    "code": 422,
    "message": "缺少必要变量: language, focus_areas",
    "errors": [
      { "field": "variables.language", "msg": "此变量为必填" },
      { "field": "variables.focus_areas", "msg": "此变量为必填" }
    ]
  }
}
```

---

### 4.7 记录使用次数 `POST /api/prompts/:id/use`

每次用户使用提示词后调用，使 `usage_count` +1。

**成功响应 `200 OK`：**
```json
{
  "data": {
    "id": 1,
    "usage_count": 43
  }
}
```

---

### 4.8 收藏/取消收藏 `PUT /api/prompts/:id/favorite`

切换收藏状态。

**成功响应 `200 OK`：**
```json
{
  "data": {
    "id": 1,
    "is_favorite": true
  }
}
```

---

## 5. 分类模块 `/api/categories`

### 5.1 获取分类树 `GET /api/categories`

获取当前用户的分类树结构。需通过 `type` 参数指定模块。

**查询参数：**

| 参数 | 类型   | 必填 | 说明                           |
| ---- | ------ | ---- | ------------------------------ |
| type | string | 是   | `'note'` 或 `'prompt'`        |

**请求示例：**
```http
GET /api/categories?type=note
```

**成功响应 `200 OK`：**
```json
{
  "data": [
    {
      "id": 1,
      "name": "技术",
      "type": "note",
      "parent_id": null,
      "sort_order": 1,
      "children": [
        {
          "id": 2,
          "name": "前端",
          "type": "note",
          "parent_id": 1,
          "sort_order": 1,
          "children": []
        },
        {
          "id": 3,
          "name": "后端",
          "type": "note",
          "parent_id": 1,
          "sort_order": 2,
          "children": []
        }
      ]
    },
    {
      "id": 4,
      "name": "生活",
      "type": "note",
      "parent_id": null,
      "sort_order": 2,
      "children": []
    }
  ]
}
```

---

### 5.2 创建分类 `POST /api/categories`

**请求体：**
```json
{
  "name": "数据库",
  "type": "note",
  "parent_id": 1,
  "sort_order": 3
}
```

| 字段      | 类型    | 必填 | 说明                      |
| --------- | ------- | ---- | ------------------------- |
| name      | string  | 是   | 1-100 字符                |
| type      | string  | 是   | `'note'` 或 `'prompt'`    |
| parent_id | integer | 否   | 父分类 ID，不传则为根分类 |
| sort_order| integer | 否   | 同级排序序号，默认 0      |

**成功响应 `201 Created`：**
```json
{
  "data": {
    "id": 8,
    "name": "数据库",
    "type": "note",
    "parent_id": 1,
    "sort_order": 3,
    "created_at": "2026-07-01T14:00:00Z"
  }
}
```

---

### 5.3 更新分类 `PUT /api/categories/:id`

**请求体：**
```json
{
  "name": "数据库与存储",
  "sort_order": 1
}
```

**成功响应 `200 OK`：**
```json
{
  "data": {
    "id": 8,
    "name": "数据库与存储",
    "sort_order": 1
  }
}
```

---

### 5.4 删除分类 `DELETE /api/categories/:id`

> ⚠️ 删除分类后，该分类下的笔记/提示词的 `category_id` 会被置为 `NULL`（`ON DELETE SET NULL`）。

**成功响应 `204 No Content`**

---

> **文档维护者：** ResourceHub Team  
> **相关文档：** [数据库设计.md](数据库设计.md) · [开发计划与路线图.md](开发计划与路线图.md)

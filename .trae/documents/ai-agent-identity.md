# AI 智能体身份层：记忆 + 人格 + 主动性

> 目标：把 ResourceHub 从「会聊天的知识库」升级为「记得你、有性格、会主动」的个人智能体。
> 范围：长期记忆、人格配置、一个主动任务（每日知识回顾）。
> 不包含：多智能体切换、知识图谱、多源摄入、复杂调度 UI。

## Context

当前 AI 工作台已具备 RAG 检索、工具调用、人在环确认、会话留痕，但每轮对话从零开始，
没有长期记忆、没有人格设定、没有主动行为。竞赛叙事需要补齐这三块，形成最小闭环。

已核实的地基：

- `note_chunks` / `ai_conversations` / `ai_messages` / `ai_runs` / `ai_usage_logs` 已存在。
- 迁移 head 为 `9f2c7d41ab03`。
- 注入点位于 `ChatService._build_messages` 与 `AgentService._stream_events`。
- 检索层已有 `tokenize` 与 BM25 实现，可复用于记忆检索。
- 前端会话已用 `sessionStorage` 持久化，流式请求由 `useSSE` 承载。

## 一、数据模型

新增三张表，迁移 `down_revision = '9f2c7d41ab03'`。

### agent_profiles

| 字段 | 类型 | 说明 |
|---|---|---|
| id / user_id | Integer | 归属隔离 |
| name | String(50) | 智能体名字 |
| persona | Text | 角色定位 |
| tone | String(20) | 严谨 / 轻松 / 激励 |
| expertise | String(200) | 专业领域 |
| boundaries | Text | 禁区 |
| greeting | String(200) | 空态问候语 |
| is_default | Boolean | 当前激活人格 |
| created_at / updated_at | DateTime | |

MVP 只使用 `is_default` 的人格；表结构支持后续多智能体。

### agent_memories

| 字段 | 类型 | 说明 |
|---|---|---|
| id / user_id / profile_id | Integer | profile_id 可空，空为全局记忆 |
| memory_type | String(20) | fact / preference / goal / event |
| content | Text | 记忆正文 |
| embedding | Text | JSON 向量，可空降级 BM25 |
| importance | Integer | 1-5 |
| source | String(20) | conversation / manual / note |
| source_conversation_id | Integer | 溯源 |
| last_used_at / use_count | DateTime / Integer | 衰减与热度 |
| expires_at | DateTime | 可空 |
| created_at / updated_at | DateTime | |

索引：`(user_id, memory_type)`、`(user_id, importance)`。

### agent_proactive_messages

| 字段 | 类型 | 说明 |
|---|---|---|
| id / user_id | Integer | |
| kind | String(30) | daily_review / stale_goal |
| title | String(200) | |
| content | Text | |
| status | String(20) | unread / read / dismissed |
| source_ref | String(100) | 去重依据 |
| created_at | DateTime | |

索引：`(user_id, status, created_at)`。

## 二、后端服务

### persona_service.py

- `get_active(db, user_id)`：返回默认人格，无则返回内置兜底人格。
- `build_persona_prompt(profile)`：生成身份系统段。
- CRUD + `activate`（同一用户只保留一个默认人格）。

### memory_service.py

- `extract_in_background(user_id, conversation_id)`：独立会话，取最近 12 条消息，
  调 `AI_FAST_MODEL` 抽取 JSON，精确去重 + 向量去重后入库；超上限按 importance 淘汰。
- `retrieve(db, user_id, query, top_k)`：复用 `tokenize` / `_bm25_scores`，
  有向量时 RRF 融合，返回 top-k 并更新 `last_used_at`。
- `build_context(memories)`：包装 `<memory_context>`，注入前 `mask_pii`。
- CRUD：列表、手动新增、编辑、删除、清空。

### proactive_service.py

- `daily_review(db, user_id)`：最近 5 篇笔记 + 目标记忆，生成今日回顾与建议。
- `scan_stale_goals(db, user_id)`：超过 30 天且 importance >= 3 的目标生成提醒，7 天内去重。
- `list / mark_read / dismiss`。

### proactive_scheduler.py

为保证单进程部署稳定且不新增依赖，调度使用 lifespan 内的 asyncio 定时循环：
每天 `AI_PROACTIVE_HOUR`（默认 8 点，Asia/Shanghai）遍历有笔记且已配置 AI 的用户。
`ENV=test` 时不启动。多 worker 部署需改为独立调度进程。

## 三、注入点

| 位置 | 改法 |
|---|---|
| `chat_service._build_messages` | 系统段顺序：人格 → SYSTEM_GUARD → 记忆上下文 → 笔记上下文 |
| `agent._stream_events` | AGENT_SYSTEM 前拼接人格，用户目标前拼接记忆上下文 |
| `safety.py` | 新增 `wrap_memory_context()`，并声明记忆中的指令不可执行 |

记忆检索与笔记检索并行执行，避免串行增加首字延迟。

## 四、API

全部挂在 `/api/ai` 下，沿用 `success_response`：

```
GET/POST/PUT/DELETE  /api/ai/profiles
PUT                  /api/ai/profiles/{id}/activate
GET/POST/PUT/DELETE  /api/ai/memories
POST                 /api/ai/memories/extract
GET/PUT              /api/ai/proactive/messages
POST                 /api/ai/proactive/scan
```

错误码在 7xxx 段追加：7007 人格不存在、7008 记忆不存在、7009 记忆数量已达上限、7010 主动消息不存在。

`/api/ai/status` 增加 `active_profile` 与 `unread_proactive_count`。

## 五、前端

| 文件 | 改动 |
|---|---|
| `api/ai.ts` | 补 profile / memory / proactive 方法与类型 |
| `stores/agentIdentity.ts` | 新建：人格、记忆、未读计数 |
| `components/ai/AgentProfilePanel.vue` | 人格编辑表单 |
| `components/ai/MemoryPanel.vue` | 记忆列表 + 筛选 + 删除 + 手动添加 |
| `components/ai/ProactiveInbox.vue` | 主动消息列表 + 已读 |
| `views/AI/Workspace.vue` | 顶部显示智能体名字与问候；右上「智能体设置」三 Tab 抽屉 |
| `components/NavBar.vue` | AI 入口未读红点 |
| `views/Dashboard.vue` | 新增「AI 主动提醒」卡片 |

## 六、安全与隐私

- 记忆默认开启，每条可见、可删、可一键清空。
- 抽取前与注入前均做 `mask_pii`。
- 记忆置于 `<memory_context>` 不可信区块。
- 记忆数量上限 + 重要度淘汰。
- 抽取使用 `AI_FAST_MODEL`，且对话满 4 条消息才触发。
- 所有查询强制 `user_id` 过滤。

## 七、测试

| 文件 | 覆盖 |
|---|---|
| `test_agent_persona.py` | CRUD、归属隔离、默认人格唯一、兜底 |
| `test_agent_memory.py` | 抽取去重、上限淘汰、检索隔离、删除、注入格式 |
| `test_agent_proactive.py` | 列表、已读、扫描去重、无笔记跳过 |

Provider 一律通过 `monkeypatch` 替换，不触网。

## 八、实施顺序

1. 模型 + 迁移 + 错误码 + schema
2. 人格 CRUD + 注入
3. 记忆抽取 + 检索 + 注入
4. 主动消息 + 调度
5. 前端三面板 + 工作台 + Dashboard/NavBar
6. 测试 + 演示打磨 + 文档

## 九、演示脚本

1. 打开 AI 工作台，顶部显示「阿枢 · 你的前端学习搭档」。
2. 提问一个只有笔记里才有答案的问题，回答带引用。
3. 打开「记忆」面板，展示它已记住「你在学 Vue 3」。
4. 点「主动扫描」，收件箱弹出「你三个月前立的目标还没完成」。
5. 回到 Dashboard，看到未读红点与「AI 主动提醒」卡片。

# ResourceHub 云端知识库迭代优化方案

> 版本：v1.0 ｜ 日期：2026-11-04 ｜ 性质：规划文档（不涉及代码变更）
> 对标产品：Notion（块编辑 / 数据库视图 / 双向链接 / 模板体系）、飞书文档（实时协作 / 多维表格 / 权限管理 / 跨应用打通）
> 基线：基于当前代码库实际架构（FastAPI + Vue3/TipTap + MySQL 5.7）制定，所有改造点均已核对现有实现

---

## 一、方案总览

### 1.1 定位演进

```
当前：个人知识管理 + AI 提示词库（单人多端，广场静态分享）
  ↓
目标：云端知识库（多人协作、块级编辑、结构化视图、生态打通）
      核心差异化保留：AI 工作台（RAG 问答 / Agent 人在环 / 记忆 / 主动消息）
      —— Notion AI 与飞书智能伙伴均按量收费，本项目的低成本 AI 层是竞争壁垒，迭代中只增强不动摇
```

### 1.2 三阶段路线图

| 阶段 | 周期 | 主线 | 一句话目标 |
|------|------|------|-----------|
| 一、MVP 验证期 | 第 1–6 周 | 块编辑器 v1 + 双向链接 + 模板 + 基础共享权限 | 单人体验追平 Notion 核心手感 |
| 二、核心能力完善期 | 第 7–16 周 | 实时协同（Yjs）+ 集合视图 + 评论 @ + 权限 v2 | 多人协作可用、不丢字 |
| 三、生态扩展期 | 第 17–28 周 | Open API + Webhook + IM 打通 + 公开发布页 | 成为个人/小团队的"连接器" |

---

## 二、核心功能对标分析

### 2.1 Notion 能力对标

| Notion 特性 | 官方参考要点 | 当前项目实现 | 缺口等级 | 差距说明 |
|-------------|-------------|-------------|:---:|----------|
| 块编辑器 | 万物皆块；拖拽排序、`/` 菜单、Turn into、嵌套块、块 ID | [WysiwygEditor.vue](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/WysiwygEditor.vue) 仅 TipTap StarterKit + Placeholder（标题/列表/代码块等基础节点） | 🔴 高 | 无块操作（拖拽手柄、斜杠菜单、转换类型）、无稳定块 ID、内容以整篇文本存储 |
| 数据库视图 | Table/Board/Calendar/Gallery 多视图、筛选排序、属性体系、关联汇总 | 笔记 = 单文档 + 分类树 + 标签字符串（[note.py](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/backend/app/models/note.py)）；无任何集合视图 | 🔴 高 | 缺"集合"概念；标签是 JSON 字符串无法聚合；无状态/日期等结构化字段 |
| 双向链接 | `[[` 反链、链接自动补全、Backlinks 面板、关系图谱 | 无 | 🔴 高 | 笔记间没有任何引用关系模型 |
| 模板体系 | 页面模板库、`/template` 按钮插入、每周循环模板 | 无笔记模板；提示词侧有变量预设（PromptPreset）可借鉴 | 🟡 中 | 模板数据结构可复用 PromptPreset 模式，成本低 |
| 页面分享/权限 | 成员级 read/comment/edit、公开链接 + 评论区 | 广场仅"私有/公开"二值 + fork 快照（[plaza_service.py](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/backend/app/services/plaza_service.py)） | 🟡 中 | 无按用户授权、无评论、公开即全文快照 |

### 2.2 飞书文档能力对标

| 飞书特性 | 官方参考要点 | 当前项目实现 | 缺口等级 | 差距说明 |
|----------|-------------|-------------|:---:|----------|
| 实时协同编辑 | 多人同时编辑、光标署名、离线自动合并（OT/CRDT） | 完全没有；编辑走"整篇保存 + 自动保存拦截" | 🔴 高 | 需引入协同引擎（Yjs），并改造保存链路 |
| 多维表格 | 字段类型丰富、看板/甘特/表单视图、自动化 | 无 | 🟡 中 | 不做全量复刻，用"笔记集合视图"覆盖 80% 场景（见 3.2） |
| 文档权限管理 | 所有者/编辑/评论/阅读四级、链接分享范围、水印 | JWT 单一所有者模型，路由内联校验 user_id | 🔴 高 | 缺集中式权限服务与角色模型 |
| 跨应用打通 | 文档↔IM↔日历↔审批联动、机器人 Webhook | 仅有内部主动消息（proactive_scheduler）；无对外 API | 🟡 中 | 有现成调度器与 SSE 基建，做对外 webhook 成本可控 |

### 2.3 差距结论（决定阶段划分）

1. **编辑器手感与知识网络（Notion 式单人体验）是第一步**——不依赖多人体系，改动集中在[前端](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src)与 notes 存储模型，风险最低、体感最强。
2. **实时协同是最大技术跃迁**——需要新引擎、新存储表、新部署组件，必须独立成阶段并在 MVP 期先做技术预研。
3. **AI 层是护城河**——所有阶段同步增强：块级 AI 问答、协同摘要、AI 自动打标生成结构化字段（对标 Notion AI autofill）。

---

## 三、分阶段迭代路径

### 3.1 阶段一：MVP 验证期（第 1–6 周）

**目标：** 单人使用体验对齐 Notion 核心手感；为协同铺路（块 ID、内容格式双轨）。

| 优先级 | 迭代项 | 对标参考 | 交付物 | 成本预估 | 预期价值 |
|:---:|--------|----------|--------|:---:|----------|
| P0 | **块编辑器 v1**：`/` 斜杠菜单（10+ 块类型）、拖拽排序、Turn into、任务列表、Callout、分割线 | Notion block ops | WysiwygEditor 升级版 + 块操作 UI | 12–15 人日 | 编辑效率显著提升，产品演示第一印象 |
| P0 | **块 ID 落地**：顶层块注入稳定 `data-block-id`，存储格式双轨（保留 markdown `content`，新增 `content_json`） | Notion 块模型 | notes 表加 `content_format`/`content_json` 字段（Alembic 迁移） | 4–5 人日 | 后续反链/评论/协同光标全部依赖它，是地基 |
| P1 | **双向链接**：`[[` 触发笔记搜索补全；保存时抽取链接写入 `note_links` 表；右侧 Backlinks 面板 | Notion [[ wiki-links | 链接模型 + 补全弹层 + 反链面板 | 8–10 人日 | 知识网络化的起点，知识库核心卖点 |
| P1 | **笔记模板**：模板库页 + 新建时选择模板 + "另存为模板" | Notion 模板库 | 复用 PromptPreset 结构建 `note_templates` 表 | 4–6 人日 | 降低冷启动成本，团队内沉淀 SOP |
| P2 | **基础共享**：笔记级"邀请成员"（可查看/可编辑两档），落地最小 ACL | 飞书文档分享面板 | `note_shares` 表 + 分享弹窗 | 6–8 人日 | 为阶段二协同提供权限前提 |
| P2 | **协同技术预研**：Yjs + Hocuspocus POC（独立分支跑通双端合并） | 飞书协同 | POC 仓库 + 技术评审结论 | 5 人日 | 消除阶段二最大不确定性 |

**验收标准：**
- 斜杠菜单块类型 ≥ 10 种；块插入/拖拽响应 ≤ 100ms；输入延迟 ≤ 50ms（见第六节指标）
- `[[` 补全在 200ms 内返回候选（本地索引）；反链面板数据与 `note_links` 表一致率 100%
- 老笔记打开无回归：markdown 渲染路径（[markdown.css](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/styles/markdown.css) `.rh-markdown`）继续可用，广场详情渲染不回退
- 后端测试全绿（`uv run pytest -v`），新增迁移在 SQLite/MySQL 5.7 双库通过

### 3.2 阶段二：核心能力完善期（第 7–16 周）

**目标：** 多人实时协同可用且不丢字；结构化组织方式（集合视图）上线；权限体系成型。

| 优先级 | 迭代项 | 对标参考 | 交付物 | 成本预估 | 预期价值 |
|:---:|--------|----------|--------|:---:|----------|
| P0 | **实时协同引擎**：自托管 Hocuspocus（Yjs WebSocket 网关）容器 + 更新日志表 + 快照持久化到 MySQL | 飞书协同编辑 | `yjs_updates`/`yjs_snapshots` 表 + ws 网关服务 + 前端 Provider 接入 | 18–25 人日 | 从"个人工具"跃迁为"协作工具"的质变点 |
| P0 | **协同体验件**：在线成员头像栏、协作者光标署名、断线重连自动同步 | 飞书光标/_presence | awareness 接入 + 顶栏头像组件 | 5–6 人日 | 协同"看得见"，信任感来源 |
| P1 | **笔记集合视图（轻量多维表）**：对笔记集合提供 网格/看板 两类视图，字段映射 = 标签/状态/更新时间；支持筛选、排序、视图保存 | 飞书多维表格（取舍版）、Notion database | `note_collections` + `collection_views` 表 + 集合页 UI | 15–20 人日 | 结构化管理任务/资料库，覆盖多维表格 80% 高频场景 |
| P1 | **评论与 @**：笔记级评论流 + 选中内容锚点评论 + `@成员` 通知 | 飞书评论/Notion comment | `comments` 表 + 侧边评论栏 + 站内通知 | 10–12 人日 | 协作反馈闭环，激活广场之外的协作 |
| P1 | **权限体系 v2**：集中式 `permission_service.can(user, resource, action)`；角色 = 所有者/编辑/评论/阅读；所有业务路由改为统一依赖注入鉴权 | 飞书权限模型 | 权限服务 + 全路由改造 + 权限审计日志表 | 10–12 人日 | 安全性收敛到单点，越权风险归零（当前 67 处内联校验收敛） |
| P2 | **笔记版本历史**：复用提示词版本模式（[prompt_versions](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/backend/app/models/prompt.py)）为笔记做快照 + diff | Notion page history | `note_versions` 表 + 版本面板（复用 VersionHistoryPanel 交互） | 6–8 人日 | 误删/误改兜底，协同安全感 |

**验收标准：**
- **协同冲突处理成功率 ≥ 99.9%**：双人并发编辑同一块 1000 轮压测，CRDT 合并后无内容丢失、无编辑器崩溃；断网 5 分钟内恢复后增量自动同步，零丢字
- 协同同步延迟：光标 presence ≤ 200ms（p95），内容同步 ≤ 300ms（p95，同城网络）
- 集合视图：切换视图 ≤ 300ms；看板拖拽改状态后 1s 内落库并广播
- 权限：以非授权账号访问受限笔记，403 覆盖率 100%（补专项测试用例）
- nginx.conf 补 WebSocket upgrade 配置并验证（现有 `/api/` SSE 长超时配置已具备相近基础）

### 3.3 阶段三：生态扩展期（第 17–28 周）

**目标：** 对外可集成、可自动化、可公开发布；AI 能力深度嵌入知识工作流。

| 优先级 | 迭代项 | 对标参考 | 交付物 | 成本预估 | 预期价值 |
|:---:|--------|----------|--------|:---:|----------|
| P0 | **Open API + 个人访问令牌**：笔记/集合/评论的 REST API + Token 管理（对标 Notion API 的精简版） | Notion Integrations | `/api/open/v1/*` + `api_tokens` 表 + API 文档 | 12–15 人日 | 生态前提；个人自动化（脚本备份、跨工具同步）需求真实存在 |
| P0 | **Webhook 事件**：笔记创建/更新/评论/发布等事件推送 | 飞书开放平台事件 | `webhooks` 表 + 投递器（重试 + 签名） | 8–10 人日 | 让外部系统（IM 机器人、Zapier 类工具）接得住 |
| P1 | **IM 打通**：飞书/企业微信群机器人接收 Webhook → 发文档卡片；@机器人检索笔记（复用 RAG） | 飞书文档↔IM 联动 | 机器人适配器 + 卡片模板 | 8–10 人日 | 知识库进入日常聊天动线，触达率倍增 |
| P1 | **AI 增强闭环**：块级"继续写/总结选中"；AI 自动生成标签与状态建议（对标 Notion AI autofill）；协同会话结束自动生成变更摘要 | Notion AI / 飞书智能伙伴 | AI 服务层（[provider.py](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/backend/app/services/ai/provider.py)）扩展 3 个场景 | 10–12 人日 | 差异化护城河加深；单位成本远低于竞品 AI 附件费 |
| P2 | **公开发布页**：指定笔记生成公开链接（可设密码/有效期），只读渲染 + 反应 | Notion Publish to web | 发布路由 + 只读渲染页 | 6–8 人日 | 对外分享升级（当前广场 fork 是复制，发布页是引用） |
| P2 | **知识图谱视图**：基于 `note_links` 力导向图，节点点击跳转 | Notion/obsidian graph | ECharts graph 图组件（复用 [useChart.ts](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/composables/useChart.ts)） | 5–6 人日 | 知识网络可视化，品牌记忆点 |

**验收标准：**
- Open API 全量端点有契约测试；令牌撤销即时生效；限流（复用每日配额模式）生效
- Webhook 投递成功率 ≥ 99%（7 天窗口），失败自动重试 3 次并落死信记录
- IM 机器人端到端演示：群里 @机器人提问 → 返回带引用来源的笔记答案
- 公开发布页可被无登录状态访问，权限边界测试通过

---

## 四、技术架构适配方案

### 4.1 编辑器内核（改造要点）

| 要点 | 现状 | 改造方案 |
|------|------|----------|
| 内核选型 | TipTap 3（ProseMirror 封装）已引入（[package.json](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/package.json)） | **不换内核**，叠加官方/社区扩展：Suggestion（斜杠菜单）、dropcursor+手柄、task-list、table。TipTap 与 Yjs 官方适配（y-prosemirror）成熟，为阶段二铺路 |
| 内容格式 | 单 `content` Text 列（Markdown/HTML，广场用 markdown-it 渲染） | 双轨制：新增 `content_json`（ProseMirror 文档 JSON）为权威格式；`content` 降级为"渲染/搜索兼容快照"，保存时由 JSON 序列化导出。加 `content_format` 字段灰度迁移 |
| 块 ID | 无 | 顶层块节点 attr 注入 `id`（uuid v4，新建时生成、粘贴时保持），用于反链、块评论、协同位置定位 |
| 性能护栏 | 编辑器整篇重渲染 | 大文档（>500 块）按需启用虚拟化策略；输入路径严禁全文档 JSON.stringify（防抖序列化，仅在保存节拍点执行） |

### 4.2 实时协同引擎（改造要点）

```
前端 (TipTap + y-prosemirror + y-websocket)
        │  ws（nginx upgrade 透传）
        ▼
Hocuspocus 网关容器（新增，独立于 FastAPI 进程）
        │  定期快照 + 增量落库
        ▼
MySQL 5.7：yjs_updates(doc_id, seq, update BLOB)  ← 追加式
           yjs_snapshots(doc_id, state BLOB, clock) ← 压缩快照
           快照间隔：每 50 条更新或 30s 取早到者；加载时 snapshot + 增量重放
```

- **选 CRDT（Yjs）而非 OT**：离线可编辑、无需中心化序列器，小团队实现复杂度低一个量级；官方有 Hocuspocus 自托管方案，与现有 Docker Compose（[docker-compose.yml](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/docker-compose.yml)）可直接加一个 service
- **权限前置**：WebSocket 建连时回调 FastAPI 校验 `note_shares` 权限，无权限拒绝连接；协同写权限 = 编辑档及以上
- **与现有保存链路关系**：协作文档走协同通道（快照持久化即保存），单人笔记仍走现有 REST 保存，两链路并存互不干扰；RAG 增量索引钩子挂在"快照落库后"事件上，沿用 [index_service](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/backend/app/services/ai/index_service.py) 的按用户串行锁约束
- **MySQL 5.7 约束**：更新体用 `LONGBLOB`；避免依赖 JSON 函数新特性；连接池复用现有 `connect_timeout=5` 经验

### 4.3 数据存储结构（改造要点）

新增表（均走 Alembic，遵守"MySQL 5.7 TEXT 无 DEFAULT → 应用层填充"项目约束）：

| 表 | 关键字段 | 用途 |
|----|----------|------|
| `note_blocks` | note_id, block_id, type, text_snippet, pos | 块级索引：反链/块评论/搜索定位，避免全文扫描 |
| `note_links` | src_note, src_block, dst_note, created_at | 双向链接边表；反向查询 = backlinks |
| `note_shares` | note_id, user_id, role(read/comment/edit) | 最小 ACL |
| `workspace_members` | workspace_id, user_id, role(owner/admin/member) | 阶段二引入工作域概念 |
| `comments` | note_id, block_id?, user_id, body, reply_to | 评论与回复 |
| `note_collections` / `collection_views` | 集合定义 + 视图配置（JSON：筛选/排序/分组字段） | 轻量多维表 |
| `note_versions` | note_id, version_number, snapshot(JSON), message | 版本历史（复用提示词版本交互） |
| `yjs_updates` / `yjs_snapshots` | 见 4.2 | 协同持久化 |
| `api_tokens` / `webhooks` / `webhook_dead_letters` | token hash / url+events+secret / 死信 | 生态层 |
| `audit_logs` | user_id, action, resource, at | 权限审计 |

策略与护栏：
- 向量仍存 JSON 文本（沿用既有决策：>50 万 chunk 再迁移 pgvector/Qdrant）
- `note_links`/`note_blocks` 写入时机统一收口在保存/快照钩子，链接抽取规则集中在单一 service，避免散落
- 所有新表保持 `user_id` 隔离字段与既有索引风格，迁移必须含可回滚 `downgrade()`

### 4.4 权限体系（改造要点）

```
现状：67 处路由内联 user_id 校验 + 广场 visibility 二值
目标：集中式三层模型
  ┌ 工作域层：owner / admin / member（阶段二）
  ├ 资源 ACL：note_shares（read/comment/edit）逐条授权
  └ 链接层：visibility public = 匿名只读（广场/发布页复用）
```

- 新建 `app/services/permission_service.py` 提供 `can(user, resource, action)`；FastAPI 侧提供 `require_permission("note:edit")` 依赖，路由从"自己查自己判"改为声明式
- 广场逻辑（[plaza_service.py](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/backend/app/services/plaza_service.py)）纳入统一模型：public 即链接层只读
- Agent 写操作继续强制人工确认（既有约束不变），且确认后校验目标资源权限，防止"被邀请协作者通过 Agent 越权"

---

## 五、用户体验优化方向

> 设计约束沿用既有规范：`--rh-*` 令牌体系、无边框极简风、`.rh-page` 外壳、状态组件三件套（EmptyState/LoadingState/ErrorState）、界面文案口语化（权限档位显示为「可查看 / 可评论 / 可编辑」，不出现 ACL/RBAC 等术语）

### 5.1 内容创作场景

| 优化点 | 交互设计 | 对标参考 |
|--------|----------|----------|
| 斜杠菜单 | 输入 `/` 弹出分组块菜单（基础/媒体/高级三组），支持中文关键词过滤（"标题/待办/分割线"） | Notion slash menu |
| Cmd+K 快速面板 | 全局命令面板：搜笔记、跳转、新建、执行命令；`[[` 内联补全复用同一搜索服务 | Notion quick finder |
| 模板化新建 | 新建按钮 → 模板画廊（含"空白"），模板卡片带预览缩略图 | Notion templates |
| AI 行内助手 | 选中文本浮动工具条追加「AI 续写 / AI 总结 / AI 翻译」；结果以建议块插入，可采纳/重试 | Notion AI |

### 5.2 知识组织场景

| 优化点 | 交互设计 | 对标参考 |
|--------|----------|----------|
| 反链面板 | 笔记阅读态右侧 Dock 常驻「引用了此笔记」列表，点击跳转并高亮来源块 | Notion backlinks |
| 集合视图切换 | 集合页顶部 网格/看板 分段控件；看板按状态列拖拽；视图配置入口收进右上「视图」下拉 | 飞书多维表格 |
| 知识图谱 | 「关系图谱」入口：力导向图 + 缩放/拖拽 + 节点悬浮预览首行文本 | Notion graph（社区） |
| 标签治理 | 标签管理页：合并重复标签、批量改名（标签目前是 JSON 字符串，治理依赖集合视图上线后的结构化） | 飞书多维表格字段管理 |

### 5.3 团队协作场景

| 优化点 | 交互设计 | 对标参考 |
|--------|----------|----------|
| 在线感知 | 顶栏右侧头像堆叠（含自己）；悬停显示成员与其正在编辑的笔记 | 飞书 presence |
| 光标署名 | 协同编辑时他人光标带昵称色标（颜色从 `--rh-*` 调色板派生，保证主题一致性） | 飞书协作光标 |
| 评论侧栏 | 阅读态右侧评论区：块锚点评论高亮关联、@成员、未读红点；通知中心统一收口 | 飞书/Notion 评论 |
| 分享弹窗 | 「分享」→ 搜索成员 → 选权限档（可查看/可评论/可编辑，默认可查看）；已邀请列表可随时改档或移除 | 飞书分享面板 |
| 活动流 | 集合页/首页增加「最近谁改了什么」轻量动态（复用 audit_logs） | Notion updates |

---

## 六、质量与性能指标（优化后须达成）

### 6.1 性能指标

| 指标 | 目标值 | 度量方式 |
|------|--------|----------|
| 首屏 LCP（生产 HTTPS） | ≤ 2.5s（4G 中端机） | Lighthouse / web-vitals 上报 |
| 路由切换（懒加载后） | ≤ 300ms p95 | 前端埋点 |
| **编辑器输入延迟**（键入到渲染） | ≤ 50ms p95 | Performance API 长任务采样 |
| 块插入/拖拽响应 | ≤ 100ms p95 | 同上 |
| **协同光标 presence 延迟** | ≤ 200ms p95 | awareness 时间戳差值 |
| **协同内容同步延迟** | ≤ 300ms p95（同城网络） | 客户端 ack 采样 |
| 列表类 API | ≤ 300ms p95 | 后端中间件计时 |
| RAG 检索问答首字 | ≤ 1.5s p95（沿用 SSE 流式） | ai_usage_logs latency 字段 |
| WebSocket 断线重连成功率 | ≥ 99% | 网关日志 |

### 6.2 可靠性指标

| 指标 | 目标值 | 度量方式 |
|------|--------|----------|
| **协同冲突处理成功率** | ≥ 99.9%（CRDT 合并语义下目标为 100%，容忍 schema 升级边界 <0.1%） | 双端并发压测脚本 1000 轮/批 |
| 协同会话零内容丢失 | 断网/断电/刷新恢复后丢字事件 = 0 | 混沌测试用例集 |
| 服务可用性 | ≥ 99.5%（月度） | /health 拨测（现有 healthcheck 复用） |
| Webhook 投递成功率 | ≥ 99%（7 天窗口） | 投递器统计 + 死信率 |
| 测试覆盖 | 后端新增模块 ≥ 70%；前端 stores/utils 引入 vitest 首批 ≥ 40% | CI 报告 |

### 6.3 质量门禁（每阶段出口）

1. `uv run pytest -v` 全绿 + 新增用例覆盖该阶段核心路径（协同/权限/反链）
2. `npm run build`（vue-tsc 严格模式）零错误；新增组件走令牌检查（禁硬编码色值、禁 `transition: all`）
3. 迁移在 SQLite（测试）与 MySQL 5.7（生产）双库演练通过，含 downgrade
4. 生产部署按既有 Runbook：`alembic upgrade head` + 健康检查 + 冒烟（登录→新建→编辑→分享→协同双人）

---

## 七、风险与依赖

| 风险 | 等级 | 应对 |
|------|:---:|------|
| 远端 MySQL（162.14.111.9）延迟影响协同快照落库 | 🟡 | 网关容器与 DB 同机部署（服务器现状已满足）；快照异步批量写；偶发不可达时协同降级为只读并提示 |
| nginx WebSocket 升级配置缺失 | 🟡 | 阶段二首个任务：加 `proxy_set_header Upgrade/Connection` 并压测（现有 SSE 长超时配置可参考） |
| TipTap 扩展组合的维护成本（块手柄等社区包质量参差） | 🟡 | 优先官方扩展；手柄/斜杠菜单不满足时自研（ProseMirror 插件，工作量已计入 12–15 人日） |
| 内容格式双轨迁移引入渲染回归 | 🟡 | `content_format` 逐篇灰度；广场 markdown 渲染管线（markdown-it + DOMPurify）保持不动作为兜底 |
| 多人体系稀释"个人工具"定位 | 🟢 | 工作域保持轻量：不强制建团队，单人用户全程无感知（个人空间默认存在） |
| AI 成本随多人使用放大 | 🟢 | 沿用每日 token 配额（AI_DAILY_TOKEN_QUOTA）按成员累加，超限提示明天再试 |

---

## 八、与既有约束的兼容清单

- 笔记树组件、块 ID 前缀规范（cat-/note-）、NoteTree 交互约束 → 不动
- AI 相关硬约束（拒答门槛、来源标注、写操作人工确认、密钥只放后端）→ 全部沿用并扩展到新场景
- 设计令牌、状态组件、日期格式化、SSE 封装（useSSE）→ 新 UI 全部复用
- 部署约束（.env.production、alembic stamp、1Panel 端口/防火墙）→ 新增 ws 网关端口需同步放行并更新 Runbook
- MySQL 5.7 限制（TEXT 无默认值、无向量类型、死锁重试经验）→ 新表设计已遵守

---

## 附录：工作量汇总（人日）

| 阶段 | 合计 | 其中 P0 |
|------|:---:|:---:|
| 一、MVP 验证期 | 33–44 | 16–20 |
| 二、核心能力完善期 | 64–83 | 23–31 |
| 三、生态扩展期 | 49–61 | 20–25 |
| **总计** | **146–188 人日** | **59–76 人日** |

> 按 2–3 名全栈成员投入估算：阶段一约 4–6 周、阶段二约 8–10 周、阶段三约 10–12 周（可部分并行，AI 增强项可与基建项并行推进）。

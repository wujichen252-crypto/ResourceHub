# ResourceHub 云端知识库迭代优化方案 v2（开源集成优先版）

> 版本：v2.0 ｜ 日期：2026-11-04 ｜ 性质：规划文档（不涉及代码变更）
> 关系：本版**取代** [cloud-kb-iteration-plan.md](cloud-kb-iteration-plan.md)（v1 自研版）作为执行依据；v1 保留作为能力对标与需求依据
> 核心变化：在 v1 对标结论不变的前提下，将「自研」全面切换为「集成成熟开源组件 + 薄适配层」，自研预算集中到 AI 层与知识网络两个差异化域

---

## 一、v1 → v2 变化摘要

### 1.1 决策原则（集成 vs 自研判定标准）

| 判定维度 | 通过条件 |
|----------|----------|
| 许可证 | **仅接受 MIT / Apache-2.0**；AGPL/BSL/fair-code 需单独评审（见第六节红线） |
| 维护活跃度 | 近 12 个月有发布；GitHub stars ≥ 2k 或属 TipTap/ProseMirror 官方生态 |
| 技术兼容 | 支持 Vue 3，或为运行时无关的独立服务（Docker 可挂载）；不与 MySQL 5.7 冲突 |
| 资源占用 | 单台腾讯云（现有部署）内存增量可控（目标 ≤ 1GB 总增量） |
| 可替换性 | 必须封装在自研薄适配层之后（如 `search_service` 包 Meili），上游可替换 |

### 1.2 成本对比总览（人日）

| 能力域 | v1 自研方案 | v2 集成方案 | 集成组件 | 成本变化 |
|--------|:---:|:---:|----------|:---:|
| 块编辑器 | 12–15 | 6–8 | TipTap 官方免费扩展 + @tiptap/suggestion | ▼ 50% |
| 实时协同 | 18–25 | 10–12 | Yjs + Hocuspocus（自托管） | ▼ 55% |
| 全文搜索/Cmd+K | （未规划） | 6–7 | Meilisearch | 新增能力 |
| 集合视图（轻量多维表） | 15–20 | 7–9 | TanStack Table + vuedraggable | ▼ 55% |
| 权限体系 | 10–12 | 5–6（内核）+ 5–6（改造） | Casbin + SQLAlchemy Adapter | ▼ 45% |
| 知识图谱 | 5–6 | 2–3 | ECharts graph（已在栈内） | ▼ 55% |
| 图片/附件 | （未规划） | 4–5 | @tiptap/extension-image + Pillow + 本地卷 | 新增能力 |
| 双向链接 | 8–10 | 5–6 | 自研（无对口组件，但小） | ▼ 30% |
| 评论/@、Webhook、Open API、AI 增强 | 39–48 | 32–41 | 自研为主 + 官方 IM SDK | ▼ 15% |
| **合计** | **146–188** | **约 108–135** | — | **▼ ~28%，且功能范围更大** |

> 功能范围增量：v2 新增了全文搜索（Cmd+K 快速面板）、图片/附件上传、自动化引擎部署档三个 v1 未覆盖能力。

---

## 二、开源组件选型清单

### 2.1 采纳清单（全部 MIT / Apache-2.0）

| # | 组件 | 许可证 | 版本基线 | 解决的能力 | 集成方式 |
|:---:|------|--------|----------|-----------|----------|
| 1 | **Yjs** | MIT | 13.x | CRDT 协同数据结构（协同地基） | 前端依赖，y-prosemirror 桥接 TipTap |
| 2 | **Hocuspocus** | MIT | 最新 | 自托管协同 WebSocket 网关（Node 20） | 新增 docker compose 服务 `collab` |
| 3 | **Meilisearch** | MIT | v1.11+ | 中文全文搜索、错别字容错、Cmd+K 数据源 | 新增 compose 服务 `search`（仅内网） |
| 4 | **TanStack Table** | MIT | v8 | 集合网格视图（无头表格，官方 Vue 适配 `@tanstack/vue-table`） | 前端依赖 |
| 5 | **vuedraggable** | MIT | 4.x（vue3） | 看板拖拽 | 前端依赖 |
| 6 | **Casbin** | Apache-2.0 | 3.x + casbin-async-sqlalchemy-adapter | 权限模型引擎（RBAC+ACL 一体） | 后端依赖，策略存 MySQL |
| 7 | **TipTap 官方扩展包** | MIT | 3.27.x（与现有一致） | task-list、task-item、table、image、link、character-count、@tiptap/suggestion | 前端依赖（版本对齐） |
| 8 | **Pillow** | MIT-CMU | 10.x | 图片上传处理（压缩/缩略图/格式校验） | 后端依赖 |
| 9 | **ECharts graph** | Apache-2.0 | 5.6（已在栈内） | 知识图谱力导向图 | 复用 [useChart.ts](../frontend/src/composables/useChart.ts) |
| 10 | **fastapi-pagination** | MIT | 0.12+ | Open API 列表端点分页规范化 | 后端依赖（仅 open API 使用） |
| 11 | **Authlib**（可选） | Apache-2.0 | 1.5+ | GitHub 等第三方登录 | 后端依赖（阶段三可选档） |
| 12 | **Activepieces**（可选） | MIT（社区版） | 最新 | 可视化自动化引擎（消费我们的 Webhook） | 可选 compose 部署档 |

### 2.2 评估后不采用的方案（及原因）

| 方案 | 许可证/形态 | 淘汰原因 |
|------|------------|----------|
| BlockNote（Notion 风格编辑器） | MIT，但 **React 专用** | 与 Vue 3 栈不兼容；其块能力可在 TipTap 上以低成本补齐 |
| Milkdown | MIT，Vue 友好 | 与 TipTap 同层替代，迁移存量编辑器成本 > 新增扩展成本 |
| Outline / AFFiNE / AppFlowy（整套产品） | BSL / 独立应用 | 非可嵌入组件库；Outline 许可证已非开源（BSL） |
| NocoDB / Baserow（多维表格） | AGPL-3.0 | 整套应用 + AGPL 传染风险；「集合视图」用 TanStack Table 自建更贴合既有数据模型 |
| MinIO | **AGPL-3.0** | 对象存储需求用本地卷 + nginx 静态服务即可满足；如未来需对象存储优先评估 SeaweedFS（Apache-2.0） |
| n8n | Sustainable Use（fair-code，非 OSI 开源） | 若需自动化引擎，选 Activepieces 社区版（MIT）；n8n 仅在功能不满足时另行评审 |
| python-jose | MIT（现状保留） | v1 审视报告已建议升级；v2 维持「升级版本」结论，不更换库 |

---

## 三、分阶段迭代路径 v2

### 3.1 阶段一：MVP 验证期（第 1–6 周）

**目标：** 单人体验对齐 Notion 核心手感 + 搜索基建就位；为协同铺路。

| 优先级 | 迭代项 | 集成组件 | 集成要点 | 成本 | 预期价值 |
|:---:|--------|----------|----------|:---:|----------|
| P0 | 块编辑器 v1 | TipTap 官方扩展（#7） | 增装 task-list/table/image 等 6 个官方扩展；斜杠菜单用 **@tiptap/suggestion**（MIT）自建 200 行内 Vue 组件；拖拽手柄自研小组件（ProseMirror 插件 + Vue 浮层） | 6–8 | 编辑手感质变，成本较自研减半 |
| P0 | 块 ID + 存储双轨 | 自研（必要地基） | notes 表加 `content_format`/`content_json`；顶层块注入稳定 id；Alembic 迁移 | 4–5 | 反链/评论/协同共同前提 |
| P0 | **Meilisearch 集成** | Meilisearch（#3） | compose 新增 `search` 服务（内网不暴露宿主端口，`MEILI_NO_ANALYTICS=true` + master key 入 `.env.production`）；`search_service.py` 薄适配层；同步钩子挂在笔记保存/协同快照落库后（复用 BackgroundTasks 模式，与 RAG 索引同点位）；删除笔记同步删文档 | 4–5 | 搜索从 LIKE 升级为容错中文全文检索 |
| P1 | Cmd+K 快速面板 | Meilisearch + 自研 UI | 全局命令面板（搜笔记/跳转/新建）；`[[` 补全复用同一搜索 API（输入 ≤ 200ms 出候选） | 2 | Notion quick finder 体验 |
| P1 | 双向链接 | 自研（小体量） | `[[` 触发搜索补全 → 保存时抽链写 `note_links` → Backlinks 面板 | 5–6 | 知识网络起点 |
| P1 | 笔记模板 | 自研（复用 PromptPreset 模式） | 模板库 + 新建选模板 + 另存为模板 | 3–4 | 降低冷启动成本 |
| P2 | **图片/附件上传** | TipTap image 扩展 + Pillow（#8） | FastAPI 上传端点（类型/大小校验）+ Docker 卷 + nginx 静态服务路径；粘贴即传 | 4–5 | 补齐文档基本功（v1 缺口） |
| P2 | 基础共享 + Casbin 内核 | Casbin（#6） | 引入 casbin-async-sqlalchemy-adapter；先落 note_shares（可查看/可编辑）最小模型 + `permission_service` 适配层 | 5–6 | 阶段二全路由改造的地基 |
| P2 | 协同 POC | Yjs + Hocuspocus（#1/#2） | 独立分支：Hocuspocus 跑通双人合并 + MySQL 持久化适配器最小实现 | 3 | 消除阶段二不确定性 |

**阶段合计：约 36–44 人日（v1 同期 33–44，但多交付搜索与图片两个能力域）**

**验收标准（在 v1 基础上新增）：**
- 斜杠菜单 ≥ 10 种块类型；块插入 ≤ 100ms；输入延迟 ≤ 50ms p95
- Meili 搜索 P95 ≤ 80ms（本机内网）；保存后索引同步延迟 ≤ 2s；错别字容错可用（"笔记"输成"笔计"仍可命中）
- 老笔记渲染零回归（`.rh-markdown` 管线不动）；`uv run pytest -v` 全绿
- Casbin 模型文件入库评审；越权访问用例 100% 拦截

### 3.2 阶段二：核心能力完善期（第 7–16 周）

**目标：** 多人实时协同可用不丢字；集合视图上线；权限体系成型。

| 优先级 | 迭代项 | 集成组件 | 集成要点 | 成本 | 预期价值 |
|:---:|--------|----------|----------|:---:|----------|
| P0 | 实时协同引擎 | Hocuspocus + Yjs（#1/#2） | compose 新增 `collab` 服务（node:20-alpine，仅内网）；**MySQL 5.7 持久化适配器**：`yjs_updates`（LONGBLOB 追加）+ `yjs_snapshots`（每 50 条更新或 30s 压缩快照）；建连回调经 FastAPI 校验 note_shares 权限 | 8–10 | 质变点，自研成本降 55% |
| P0 | nginx WebSocket 透传 | 配置改造 | `/collab` location 加 Upgrade/Connection 头；内网端口不公网暴露 | 1 | 协同通路 |
| P0 | 协同体验件 | y-prosemirror awareness | 在线头像堆叠、光标署名（颜色从 `--rh-*` 派生）、断线重连自动同步 | 4–5 | 协同"看得见" |
| P1 | 集合视图（轻量多维表） | TanStack Table + vuedraggable（#4/#5） | 网格 = @tanstack/vue-table 无头表格；看板 = vuedraggable 按状态列拖拽；视图配置（筛选/排序/分组）存 `collection_views`（JSON） | 7–9 | 覆盖多维表格 80% 高频场景 |
| P1 | 评论与 @ | 自研 | `comments` 表 + 块锚点 + 侧边评论栏 + 通知；@成员通知复用主动消息调度器 | 8–10 | 协作反馈闭环 |
| P1 | 权限体系 v2 | Casbin（#6） | 全路由从内联 user_id 校验改造为 `require_permission` 依赖注入（v1 盘点约 67 处收敛）；加审计日志表 | 5–6 | 安全单点收敛 |
| P2 | 笔记版本历史 | 自研（复用提示词版本模式） | `note_versions` 快照 + diff + 版本面板 | 5–6 | 误操作兜底 |

**阶段合计：约 38–47 人日（v1 同期 64–83，▼ 45%）**

**验收标准（新增/强化）：**
- **协同冲突处理成功率 ≥ 99.9%**：双人并发 1000 轮压测零丢字、零崩溃（Yjs CRDT 语义目标为 100%）
- 光标 presence ≤ 200ms、内容同步 ≤ 300ms（p95，同城）
- `collab` 服务内存 ≤ 300MB（50 并发文档）；快照后 MySQL 增量 ≤ 单文档 5MB
- 集合视图切换 ≤ 300ms；看板拖拽 1s 内落库广播
- Meili 与 MySQL 一致性巡检脚本：抽样 100 篇零漂移

### 3.3 阶段三：生态扩展期（第 17–28 周）

**目标：** 对外可集成、可自动化、可公开发布；AI 深度嵌入。

| 优先级 | 迭代项 | 集成组件 | 集成要点 | 成本 | 预期价值 |
|:---:|--------|----------|----------|:---:|----------|
| P0 | Open API + 令牌 | 自研 + fastapi-pagination（#10） | `/api/open/v1/*` 笔记/集合/评论端点；`api_tokens` 表（hash 存储）+ 撤销即时生效 + 限流复用配额模式 | 8–10 | 生态前提 |
| P0 | Webhook 事件 | 自研（小体量） | `webhooks` 表 + HMAC 签名投递器 + 3 次重试 + 死信表；事件负载与 Activepieces 对齐 | 6–8 | 外部系统接得住 |
| P1 | IM 打通 | 官方 SDK（MIT）：lark-oapi / wecom-cli 生态 | 群机器人收 Webhook → 文档卡片；@机器人检索（复用 RAG 管线与拒答门槛约束） | 6–8 | 知识库进入聊天动线 |
| P1 | AI 增强闭环 | 自研（差异化核心） | 块级续写/总结、AI 自动打标建议（对标 Notion AI autofill）、协同会话摘要；全部走现有 [provider.py](../backend/app/services/ai/provider.py) | 8–10 | 护城河加深 |
| P2 | 公开发布页 | 自研 | 发布链接（可设密码/有效期）只读渲染 + 反应 | 4–5 | 对外分享升级 |
| P2 | 知识图谱 | ECharts graph（#9，已在栈内） | `note_links` 力导向图 + 悬浮预览 + 点击跳转 | 2–3 | 品牌记忆点 |
| 可选 | Activepieces 自动化档 | Activepieces（#12） | 可选 compose profile：自托管自动化引擎消费 Webhook（"笔记发布 → 飞书群通知"零代码编排） | 2–3 | 无代码自动化 |
| 可选 | OAuth 登录 | Authlib（#11） | GitHub 登录（注册绑定既有账号体系） | 3–4 | 降低注册门槛 |

**阶段合计：约 36–50 人日（含可选档 5–7 人日；v1 同期 49–61）**

**验收标准：**
- Open API 全端点契约测试 + 令牌撤销即时生效
- Webhook 投递成功率 ≥ 99%（7 天窗口）
- IM 端到端演示：群内 @机器人提问 → 带来源的笔记答案（不相关内容明确拒答——沿用既有 AI 约束）

---

## 四、技术架构适配 v2（部署拓扑增量）

### 4.1 compose 服务增量

```
现有：backend(FastAPI:8000) / frontend(nginx:9200) / MySQL(1Panel 容器)
新增：┌ search   (getmeili/meilisearch:v1.11)   仅内网，数据卷 meili_data
      └ collab   (node:20-alpine + Hocuspocus)  仅内网，经 nginx /collab 透传
```

- 两个新服务**均不暴露宿主端口**，仅挂 `resourcehub-network` 内网；对外仅 nginx 443 入口
- 内存预算：Meili ≤ 500MB（小数据集）+ Hocuspocus ≤ 300MB → 总增量 ≤ 1GB（判定标准红线内）
- 两者均配 healthcheck（Meili `/health`；Hocuspocus 自实现 `/health` HTTP 探针），复用 `python:3.10-slim 无 curl` 教训 → Node 服务用内置 http 探针

### 4.2 数据流与一致性

```
笔记保存(REST) ──┐
                 ├→ BackgroundTasks → RAG 索引(600字分块, 不变)   ← AI 问答用
协同快照落库 ────┘                 └→ Meili 同步(整篇文本轻量索引)  ← 搜索/Cmd+K/[[补全用
```

- 两路索引共享同一钩子点位，`search_service` 失败不影响主流程（记日志 + 巡检补偿）
- 搜索服务不可用时降级：`search_service` fallback 到现有 LIKE 查询（适配层价值）

### 4.3 MySQL 5.7 约束延续

- `yjs_updates.update` 用 `LONGBLOB`；所有新表 TEXT 列不设 DEFAULT（应用层填充）
- Casbin 策略表由 adapter 自动建表，迁移统一纳入 Alembic 管理
- 协同相关写路径复用「按用户串行锁 + 死锁重试」既有经验

---

## 五、用户体验优化 v2

与 v1 完全一致（三场景优化点、界面约束、口语化文案原则均沿用 v1 第五节），仅两处因集成而调整：

| 优化点 | v2 调整 |
|--------|---------|
| Cmd+K 快速面板 | 数据源从「自建搜索」改为 Meilisearch，错误容错与中文分词开箱即用，交互不变 |
| 集合视图 | 网格交互向 TanStack Table 默认行为对齐（列宽拖拽、列排序内置），减少自研打磨成本 |

---

## 六、许可证合规与供应链风险（v2 新增维度）

### 6.1 合规红线

1. **仅引入 MIT / Apache-2.0 依赖进主链路**；任何 AGPL/BSL/fair-code 组件引入前必须单独评审（当前采纳清单全部达标）
2. 新增依赖统一记录版本与许可证到 `pyproject.toml` / `package.json`（lock 文件已托管），不 fork 改造核心库——需要补丁时提上游 PR 或在适配层拦截
3. 商用/参赛展示场景：合规清单可随答辩材料出示，体现工程规范性

### 6.2 供应链风险与缓解

| 风险 | 等级 | 缓解 |
|------|:---:|------|
| 上游 breaking change（尤其 TipTap 3.x 大版本） | 🟡 | 版本锁定（现已是 `^3.27.4` 精确对齐）；扩展统一走官方包，避免小众社区包 |
| Hocuspocus 引入 Node.js 运行时（新运维面） | 🟡 | 独立容器隔离；健康检查 + 内存限额；适配器层保证可换 y-websocket 纯方案 |
| Meilisearch 索引与 MySQL 漂移 | 🟡 | 同钩子同步 + 巡检脚本 + LIKE 降级兜底 |
| 服务端内存超限（单机） | 🟢 | 两服务限额部署；超出则 Meili 降级为可选、搜索回落 LIKE |
| 镜像供应链（新镜像来源） | 🟢 | 仅使用官方镜像（getmeili/meilisearch、node:20-alpine），compose 内固定 tag |

---

## 七、质量与性能指标 v2

v1 第六节全部指标沿用（LCP ≤ 2.5s、输入延迟 ≤ 50ms、协同冲突成功率 ≥ 99.9%、零丢字等），新增：

| 指标 | 目标值 | 说明 |
|------|--------|------|
| Meili 搜索 P95 | ≤ 80ms | 内网本机；含 `[[` 补全场景 |
| 索引同步延迟（保存→可搜） | ≤ 2s | BackgroundTasks 异步窗口 |
| 协同网关可用性 | ≥ 99.5% | collab 服务拨测 |
| 新增测试覆盖 | 后端 search/collab 持久化适配器 ≥ 70%；前端集合视图 stores ≥ 40%（vitest） | 沿用 v1 门禁 |
| 部署冒烟扩展 | 登录→新建→编辑→**插入图片**→**Cmd+K 搜索**→分享→双人协同 | 每次发版执行 |

---

## 八、里程碑与投入汇总

| 阶段 | 周期 | v2 成本 | v1 成本 | 降幅 |
|------|------|:---:|:---:|:---:|
| 一、MVP 验证期 | 1–6 周 | 36–44 | 33–44 | 持平但多交付 2 个能力域 |
| 二、核心能力完善期 | 7–16 周 | 38–47 | 64–83 | ▼ 45% |
| 三、生态扩展期 | 17–28 周 | 36–50 | 49–61 | ▼ 20% |
| **合计** | **约 28 周** | **110–141 人日** | **146–188 人日** | **▼ ~28%** |

> 按 2–3 名全栈成员估算与 v1 一致；节省的约 35–45 人日建议投向两处：① AI 增强项加码（差异化）；② v1 审视报告中的 P0/P1 工程债清偿（Dockerfile 依赖统一、CI 建立、ESLint/Ruff 引入——集成更多组件后 CI 门禁优先级更高）。

---

## 九、与既有约束的兼容清单（继承 v1 第八节，增补）

- 新增 compose 服务遵守「1Panel 端口/防火墙」运维约束：新服务不占宿主端口，无需新增 ufw 规则
- `AI_*` 环境变量继续统一走项目根 `.env`；`MEILI_MASTER_KEY` 等新密钥入 `.env.production`（chmod 600，不入库）
- AI 拒答门槛、来源标注、Agent 写操作人工确认等硬约束全量沿用至 IM 机器人场景
- 设计令牌/状态组件/日期格式化/useSSE 等前端规范在新 UI 全量复用

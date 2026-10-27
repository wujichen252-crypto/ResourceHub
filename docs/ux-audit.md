# ResourceHub 用户体验审计报告

> 审计日期：2026-10-22
> 审计范围：前端认证、笔记、提示词、AI 工作台、设置与部署配置；后端接口健壮性、事务与安全
> 审计方式：逐文件静态走查 + 关键路径行为推演（含异常路径），每条问题均标注代码位置
> 结论口径：只记录会真实影响用户的问题，不含风格偏好

## 修复状态速览（2026-10-22 更新）

| 项 | 状态 |
|----|------|
| P0-1 索引重建超时 | 已修复，待线上验证 |
| P0-2 提示词评测超时 | 已修复，待线上验证 |
| P0-3 生产环境 AI 配置 | **未完成**：需要服务器权限，已给出操作步骤（见第九节） |
| P0-4 刷新丢失对话 | 已修复，已在浏览器实测通过 |
| 审计中新增发现：断开 SSE 后残留事务占锁 | 已修复 |

---

## 一、总体结论

本轮共确认 **17 项** 会影响用户体验的问题：**P0 4 项、P1 8 项、P2 5 项**。

最值得警惕的不是单个 bug，而是四类**系统性缺口**——它们会持续制造同类问题：

| 缺口 | 表现 | 后果 |
|------|------|------|
| 所有请求共用 10 秒超时 | 长任务（索引重建、提示词评测）必然失败 | 用户点了没反应，或看到英文超时报错，但后台其实跑完了 |
| 认证只做在 axios 通道 | AI 流式请求绕过了 axios | 登录过期后 AI 页面报 HTTP 401 原始错误，其他页面却能自动续期 |
| 长任务没有进度与恢复机制 | 只有「转圈 + 结果」两态 | 刷新/断网/切页即丢失，用户无法判断是否还在跑 |
| 验收只覆盖正常路径 | 断网、超时、过期、额度、空数据未纳入检查 | 问题在用户手里才第一次暴露 |

---

## 二、P0：直接阻断功能或造成内容丢失

### P0-1 「让 AI 重新读取笔记」按钮必定超时

- **证据**：[http.ts](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/api/http.ts#L14) 全局 `timeout: 10000`；[ai.ts](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/api/ai.ts#L119-L121) 重建索引走同一个实例；[index_service.py](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/backend/app/services/ai/index_service.py#L54-L96) 需逐条笔记分块 + 分批向量化后才能返回。
- **用户实际遭遇**：18 篇笔记约 600 个分块，需要数十次向量请求，耗时远超 10 秒。前端 10 秒即中断并弹出英文 `timeout of 10000ms exceeded`，而后端仍在继续写库；用户再点一次会叠加第二轮索引，并可能撞上并发。
- **修复建议**：长任务改用独立超时（≥180 秒），或改为「提交任务 → 前端轮询进度」；错误文案统一转成中文。
- **影响面**：AI 功能的第一道门槛，新用户第一次点就会失败。

### P0-2 提示词「开始测试」必定超时

- **证据**：[eval.ts](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/api/eval.ts#L96-L98) `run` 走 10 秒实例；[eval_service.py](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/backend/app/services/ai/eval_service.py#L184-L235) 为同步接口，逐题「生成一次 + 评审一次」，全部结束才提交。
- **用户实际遭遇**：3 道题 = 至少 6 次模型调用，正常也在 20～60 秒。前端必然先报超时；后端可能在用户已看到「失败」之后才把结果写进数据库，用户刷新才可能看到记录，行为自相矛盾。
- **修复建议**：改为异步任务 + 进度轮询（推荐），至少给该接口单独放宽超时并显示「正在逐题测试（3/3）」。
- **影响面**：整个 Prompt 实验室的核心动作。

### P0-3 生产环境尚未配置 AI 服务

- **证据**：开发环境密钥写在仓库根目录 `.env`（已被忽略），而生产 `/opt/ResourceHub/.env.production` 只配置了数据库与 `SECRET_KEY`，未同步 `AI_BASE_URL / AI_API_KEY / AI_CHAT_MODEL / AI_EMBEDDING_*`。
- **用户实际遭遇**：代码部署上线后，AI 工作台、索引、评测全部提示「还没有填写 AI 服务密钥」，即本轮所有 AI 能力在生产上等于零。
- **修复建议**：发布清单中把「AI 配置四项」列为阻塞项，部署后用 `curl /api/ai/status` 验证 `configured: true`。

### P0-4 刷新页面整段对话消失

- **证据**：会话只存在于 [aiWorkspace.ts](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/stores/aiWorkspace.ts) 内存中，未做任何持久化；`conversationId` 也未写入 URL。
- **用户实际遭遇**：生成长回答时误按 F5、浏览器崩溃、手机切后台被回收，全部内容与正在生成的回答一起消失，且无任何提示或草稿恢复。
- **修复建议**：最少做 `sessionStorage` 草稿（切页/刷新可恢复）；彻底方案是接后端已有的 `/ai/conversations` 会话表做恢复。

---

## 三、P1：明显损害体验或让用户困惑

| # | 问题 | 证据 | 用户会遇到什么 | 修复建议 |
|---|------|------|----------------|----------|
| P1-1 | 登录/注册失败弹两次相同提示 | [http.ts](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/api/http.ts#L31-L38) 已 `ElMessage.error`；[Login.vue](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Login.vue#L245-L247) 又弹一次 | 密码输错时连续出现两条「用户名或密码错误」 | 业务错误只在一处提示：拦截器提示，页面只记录状态 |
| P1-2 | 登录过期无任何提示，直接被踢回登录页 | [http.ts](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/api/http.ts#L66-L69)、[http.ts](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/api/http.ts#L94-L98) | 正在操作时页面突然变成登录页，不知道发生了什么 | 跳转前提示「登录已过期，请重新登录」，并保留回跳地址 |
| P1-3 | 多个请求同时过期会各自刷新一次 | [http.ts](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/api/http.ts#L53-L71) 每个请求自带 `_retry`，无共享 Promise | 首页同时发三四个请求时，可能连续刷新三次；若刷新令牌轮换，后两次失败导致被误踢下线 | 加「单飞」锁：同一时刻只允许一次刷新，其余请求排队复用结果 |
| P1-4 | AI 提问时登录过期只报原始 401 | [useSSE.ts](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/composables/useSSE.ts#L124-L140) 直接 fetch，未复用刷新逻辑 | 其他页面能自动续期，唯独 AI 工作台弹「请求失败（HTTP 401）」 | 抽出带刷新的 fetch 封装，401 时刷新后重放一次 |
| P1-5 | 流式回答无整体超时/心搏 | [useSSE.ts](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/composables/useSSE.ts#L150-L171) 无限等待 `reader.read()` | 网络半断、代理挂起时永远显示「正在生成」，用户只能干等或刷新 | 加空闲超时（如 90 秒无事件即提示可重试）与「重试」按钮 |
| P1-6 | 网络类错误直接显示英文原文 | [http.ts](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/api/http.ts#L73-L77) 回退到 `error.message` | 断网时看到 `Network Error`、`timeout of 10000ms exceeded` | 建错误映射表：断网/超时/5xx/429 统一中文可操作文案 |
| P1-7 | 提示词列表、详情、编辑页与设置页无窄屏适配 | 全站仅 [NotesPage.vue](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Notes/NotesPage.vue#L73-L80)、[PromptLab.vue](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Prompts/PromptLab.vue#L898) 等有 `@media`；PromptList / PromptDetail / PromptEditor / Settings 均无 | 手机上打开提示词编辑页，双栏挤压、按钮被截断 | 补 768/640 两档断点，双栏降为单栏 |
| P1-8 | 设置页没有「AI 模型设置」 | [Settings.vue](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Settings.vue) 全文无 AI/模型/密钥相关代码 | 想换模型只能改服务器配置文件并重启，与「后台可调」的目标不符 | 增加模型名、服务地址、密钥三项，保存后即时生效（密钥只写不读） |

---

## 四、P2：可优化，但不会立刻阻断

| # | 问题 | 证据 | 说明 |
|---|------|------|------|
| P2-1 | 笔记自动保存的并发保护是无效的 | [WysiwygEditor.vue](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/WysiwygEditor.vue#L113-L123) `emit` 是同步调用，`isSaving` 立刻复位，`catch` 也捕获不到异步失败 | 连续输入时可能有多个保存同时在途；建议由父组件持有保存队列或做防抖串行 |
| P2-2 | 评测额度只在开始时检查一次 | [eval_service.py](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/backend/app/services/ai/eval_service.py#L171) | 一次多题评测可能超出每日额度；建议每用例前复用 `ensure_quota` |
| P2-3 | 「等待确认」的操作无法在刷新后恢复 | [AIMessage.vue](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/ai/AIMessage.vue#L56-L70) 仅内存态，`run_id` 未持久化 | 用户刷新后该确认卡片消失，挂起的写操作无法继续 |
| P2-4 | 未设 `ENV=production` 时静默生成随机密钥 | [config.py](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/backend/app/core/config.py#L19)、[config.py](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/backend/app/core/config.py#L65-L80) | 若部署漏配 `ENV`，重启后所有用户登录态失效，且 `DEBUG` 仍为 True |
| P2-5 | 多标签页状态不同步 | 全站无 `storage` 事件监听 | 一个标签页退出登录，另一个仍显示已登录并可继续操作 |

---

## 五、已确认做对的部分（避免误改）

- 统一响应格式与全局异常兜底：[main.py](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/backend/main.py#L78-L149) 不会把 500 堆栈暴露给前端。
- 越权访问控制到位：笔记、提示词服务均按 `user_id` 过滤。
- 关联数据清理依赖数据库外键级联：`note_chunks / prompt_versions / eval_results / ai_messages` 均为 `ON DELETE CASCADE`，删笔记不会留下 AI 可引用的孤儿分块。
- 笔记保存失败有可见状态（`aria-live` 提示「保存失败，请手动保存」），离开页面前有未保存拦截，关闭标签页有 `beforeunload`。
- 主要页面已使用统一空态/骨架屏组件；404 兜底路由存在。
- 样式规范执行良好：全站无 `transition: all`、无主动移除焦点环、无散落硬编码色值。
- 用户可见文案已无技术术语残留（搜索「索引/向量/RAG/接口/Token」仅命中代码注释）。

---

## 六、根因与防复发机制

1. **请求层缺少「任务时长」维度**
   建议：保留 10 秒的普通请求实例，新增 `longRequest`（≥180 秒）或任务化接口；任何预计超过 5 秒的操作，UI 必须给进度或可离开的提示。

2. **认证逻辑只覆盖 axios**
   建议：把「带自动续期的请求」抽成一个独立函数，axios 与 SSE 共用；401 处理加单飞锁。

3. **异常路径没有验收标准**
   建议：固定 6 条冒烟场景，每次改动后手测或自动测——
   ① 断网提交 ② 请求超时 ③ 登录过期 ④ AI 未配置 ⑤ 额度用尽 ⑥ 空列表/无结果。

4. **部署清单缺少功能级检查**
   建议：发布后固定执行三项验证：`/health`、`/api/ai/status` 的 `configured`、核心页面各点一次（重建索引、发起提问、运行一次评测）。

5. **提示文案在两层重复提示**
   建议：约定「业务错误只由请求层提示一次，页面只负责展示状态」，避免双弹窗与重复打扰。

---

## 七、建议修复顺序

| 顺序 | 内容 | 理由 |
|------|------|------|
| 1 | P0-1、P0-2：长任务超时与进度 | 当前两个核心功能「必失败」，修完立刻可用 |
| 2 | P0-3：生产 AI 配置 + 部署后验证 | 决定线上 AI 是否可用 |
| 3 | P1-1、P1-2、P1-3、P1-4：提示与认证一致性 | 一次性把「被踢下线/双弹窗/401」类问题清零 |
| 4 | P0-4、P1-5、P1-6：内容恢复与断线体验 | 减少「答到一半全没了」的挫败感 |
| 5 | P1-8：设置页 AI 模型配置 | 兑现「后台可调」 |
| 6 | P1-7、P2 各项 | 移动端与细节打磨 |

---

## 八、审计覆盖范围与未覆盖项

- 已覆盖：认证与会话、笔记列表/树/编辑/保存/删除、提示词列表/详情/编辑/版本/实验室、AI 对话与自动助手、广场、设置、路由、请求层、后端主要路由与服务、迁移外键、部署配置。
- 未覆盖：真实弱网与长时间压测、并发用户下的额度与索引表现、浏览器兼容性矩阵、屏幕阅读器实测。
- 标注说明：P1-7 的移动端结论来自断点缺失的静态判断，建议在真机复核后再排期修复。

---

## 九、本轮修复记录（2026-10-22）

### 已修复

| 项 | 改动 | 验证 |
|----|------|------|
| P0-1 索引重建超时 | [http.ts](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/api/http.ts) 新增 `LONG_TASK_TIMEOUT`（300 秒）；[ai.ts](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/api/ai.ts) 的 `rebuildIndex` 单独使用；[Workspace.vue](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/AI/Workspace.vue) 重建期间提示「正在读取，可能需要几十秒，请先不要关闭页面」 | 前端构建通过 |
| P0-2 评测超时 | [eval.ts](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/api/eval.ts) 的 `run` 使用长任务超时；[PromptLab.vue](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Prompts/PromptLab.vue) 测试期间显示「正在逐题生成并评分」 | 前端构建通过 |
| P0-2 配套 | [nginx.conf](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/nginx.conf) 增加 `proxy_read_timeout 300s` 与 `proxy_buffering off`，否则网关会在 60 秒提前断开流式响应与长任务 | 配置审阅 |
| P0-4 刷新丢对话 | [aiWorkspace.ts](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/stores/aiWorkspace.ts) 用 `sessionStorage` 保存会话与未发送草稿（500ms 合并写入 + `pagehide` 补写）；刷新后恢复，被中断的回答标注「页面刷新让这次回答中断了」；退出登录时清空 | 浏览器实测：回答与草稿均恢复 |
| 新增发现：断流占锁 | [agent.py](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/backend/app/services/ai/agent.py) 与 [chat_service.py](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/backend/app/services/ai/chat_service.py) 在生成器被取消时立即 `rollback`，避免客户端断开后残留事务持续持有行锁 | 后端 66 项测试通过 |
| P1-6 英文错误 | [http.ts](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/api/http.ts) 与 [useSSE.ts](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/composables/useSSE.ts) 把断网、超时、5xx、429 统一翻译成中文可操作提示 | 浏览器实测：断流后显示「网络中断了，请检查网络后重试」 |

> 断流占锁的发现过程：清理验收账号时，`DELETE` 连续两次报 `1205 Lock wait timeout`，定位到刷新页面时被中断的自动助手任务仍持有 `ai_runs` 行锁；重启后端后立即释放。这说明「用户刷新或关页面」不仅会丢内容，还会在数据库留下锁，属于必须根治的问题，因此一并修复。

### 未完成：生产环境 AI 配置（P0-3）

当前机器没有生产服务器登录权限（`ubuntu@162.14.111.9` 公钥/密码均被拒），这一步需要你在服务器上执行：

```bash
cd /opt/ResourceHub
sudo nano .env.production        # 追加以下四项（密钥用本地 .env 里同一把）
# AI_BASE_URL=https://api.siliconflow.cn/v1
# AI_API_KEY=<你的硅基流动密钥>
# AI_CHAT_MODEL=Qwen/Qwen2.5-7B-Instruct
# AI_EMBEDDING_MODEL=BAAI/bge-m3
# AI_EMBEDDING_DIM=1024

sudo docker compose --env-file .env.production up -d --build
sudo docker compose exec backend alembic upgrade head
curl -s http://127.0.0.1:8000/api/ai/status      # 期望 configured: true
```

验证通过后，登录线上站点确认 AI 工作台状态为「AI 服务已就绪」，再点一次「让 AI 重新读取笔记」。

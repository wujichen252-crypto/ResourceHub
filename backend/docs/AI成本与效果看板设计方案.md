# AI 成本与效果看板（知识资产 ROI）— 设计与实现文档

> 状态：设计稿（待评审） ｜ 日期：2026-11-05
> 目标：把「AI 花了多少成本、知识资产产生了多少回报」从抽象概念变成可量化、可视化的看板，作为比赛项目「知识资产 ROI」创新点的落地依据。

---

## 1. 背景与目标

ResourceHub 已具备完整的 AI 能力层（RAG 问答、Agent、提示词评测、自动优化、向量化索引），并在每次调用时写入 `ai_usage_logs` 计量流水。但这些数据目前只用于**配额限制**，没有被「读懂」：

- 用户不知道自己的 token 花在了哪个功能上；
- 用户不知道哪篇笔记、哪条提示词「值得」投入 AI 成本；
- 平台无法回答「我在 AI 上的投入，换回了多少知识资产价值」这一核心问题。

**本功能要交付的是：** 一个「AI 成本与效果看板」页面，用三层数据回答 ROI 问题——

1. **成本层**：token 消耗 → 折算金额，按场景/模型/时间分布；
2. **效果层**：AI 引用笔记的次数、提示词被使用/评测得分、Agent 完成率；
3. **ROI 层**：成本 × 效果 交叉计算，给出知识资产级别的投入产出结论。

---

## 2. 现状数据基础（无需大改 schema）

| 数据 | 位置 | 对看板的作用 |
|------|------|-------------|
| 调用流水（scene/model/tokens/latency/success） | `ai_usage_logs`（`app/models/ai.py`） | 成本层主数据源，scene 已区分 chat / agent / embedding / eval / optimize |
| 检索引用（含 note_id） | `ai_messages.citations`（JSON 数组） | **效果层核心**：可统计「每篇笔记被 AI 引用多少次」，即笔记的 AI 侧产出 |
| Agent 运行结果 | `ai_runs.status`、`step_count`、tokens | 效果层：任务完成率、平均步数、单任务成本 |
| 提示词使用记录 | `PromptUsageLog`（prompt_analytics 已有 summary） | 效果层：提示词使用频次 |
| 评测得分 | `prompt_eval_results.score` | 效果层：提示词质量分 |
| 优化会话成本 | `prompt_optimization_runs.total_tokens`、`baseline_score → candidate_score` | ROI 亮点：**「花 X token 换来分数 +Y」**，可量化优化的投入产出 |
| 分块向量 | `note_chunks.token_count`、`embedding_model` | 成本层：embedding 索引维护成本按笔记归集 |
| 已有聚合服务 | `StatsService`（`app/services/stats_service.py`，Python 端日期分桶，SQLite/MySQL 双兼容） | 直接沿用同样的实现模式，保证测试环境一致 |

**结论：成本与效果的原始数据都已落库，看板主要是「聚合 + 换算 + 呈现」，schema 改动可以压到最小（见 §4）。**

---

## 3. 指标体系定义

### 3.1 成本指标

| 指标 | 计算方式 | 来源 |
|------|---------|------|
| 总 Token | `sum(total_tokens)` 按时间窗过滤 | ai_usage_logs |
| 折算金额 | `Σ(prompt_tokens × 输入单价 + completion_tokens × 输出单价)` | 单价来自模型价格表（§4.1） |
| 场景成本占比 | 按 `scene` 分组 | ai_usage_logs |
| 模型成本占比 | 按 `model` 分组 | ai_usage_logs |
| 索引维护成本 | `sum(note_chunks.token_count)` × embedding 单价（一次性 + 增量） | note_chunks |
| 失败浪费成本 | `success=false` 的调用 token 折算金额 | ai_usage_logs |

### 3.2 效果指标

| 指标 | 计算方式 | 来源 |
|------|---------|------|
| 笔记 AI 引用次数 | 解析 `ai_messages.citations` JSON，按 note_id 计数 | ai_messages |
| 活跃知识资产数 | 时间窗内被引用过 / 被检索过的去重笔记数 | ai_messages + ai_usage_logs(embedding) |
| 提示词使用次数 | PromptUsageLog 按提示词计数 | PromptUsageLog |
| 提示词质量分 | 最近一次 eval 的 score（无评测则视为未知） | prompt_eval_results |
| Agent 完成率 | `succeeded / (succeeded + failed)` | ai_runs |
| 优化收益 | `candidate_score - baseline_score`，及每 +1 分消耗的 token | prompt_optimization_runs |

### 3.3 ROI 指标（创新核心）

> ROI 的「收益」本质是主观的，我们用两个**可证实的代理指标**，保证评委可验证、不玄学：

**① 笔记级 ROI = AI 引用价值 / AI 维护成本**

```
笔记 AI 引用次数 R（近 30 天，来自 citations）
笔记索引成本 C = 该笔记 chunk token 总数 × embedding 单价（增量重嵌只算一次）
笔记 ROI 分 = R × w1 + 是否被收藏/使用 × w2 − C 归一化
```

产出「知识资产健康度」列表：
- **高产出资产**：引用多、成本低 → 值得持续维护；
- **沉睡资产**：从未被 AI 检索引用 → 提示用户「AI 从未用到这篇笔记，考虑归档或补充标签」；
- **高耗低效资产**：索引成本高但引用为 0 → 清理候选。

**② 提示词级 ROI = 质量收益 / 优化投入**

```
优化投入 = optimize scene 的 token 折算金额（按 prompt_id 归集）
质量收益 = (采纳版本得分 − 基线得分)
提示词 ROI = 使用次数 × 质量分 ÷ (1 + 优化投入归一化)
```

产出「提示词性价比排行」，让用户知道哪条提示词「便宜、好用、高质量」，哪条「烧了 token 还没提分」。

**③ 四象限场景矩阵（功能级）**

以「场景」为单位的散点图（ECharts scatter）：
- X 轴：该场景人均 token 成本；Y 轴：该场景使用频次（或评分）；
- 四象限标注：**明星**（高频低成本）/ **潜力**（低频低成本）/ **重投入**（高频高成本）/ **待优化**（低频高成本）。

---

## 4. 数据模型与配置变更（最小化）

### 4.1 模型价格表 → 配置而非新表

单价随供应商变动，**不建议建表存价格流水**。在 `app/core/config.py` 增加：

```python
# JSON 字符串，形如 {"deepseek-chat": {"input": 0.001, "output": 0.002}, "BAAI/bge-m3": {"input": 0.0001, "output": 0}}
AI_MODEL_PRICES: str = "{}"   # 单位：元 / 千 token
```

运行时解析为 dict，未配置的模型按 0 元计（看板显示「未定价」而不是误导性的 0）。
`.env.production.example` 同步补充示例。

### 4.2 `ai_usage_logs` 增加一个可空字段（唯一 schema 变更）

```python
prompt_id: Mapped[int | None] = mapped_column(
    Integer, nullable=True, comment="关联提示词 ID（eval/optimize 场景使用，用于提示词级成本归集）"
)
```

> 说明：若不想动 schema，备选方案是从 `prompt_optimization_runs.total_tokens` 与 `prompt_eval_results` 反推（按 created_at 对齐），但精度差且查询复杂，推荐直接加列（Alembic 迁移一条，见 ADR-007 流程）。

### 4.3 无需日汇总表（当前量级）

单人/小团队场景下 `ai_usage_logs` 行数有限（配额兜底），聚合直接实时查询即可，沿用 `StatsService` 的 Python 端分桶模式。若未来多用户量级上来，再加「按日汇总表」优化（文档级预留，不实现）。

---

## 5. 后端 API 设计

新增独立路由 `routers/roi.py`（避免 stats.py 职责膨胀），全部 `get_current_user` 鉴权、`success_response` 包裹，遵循现有响应规范：

| 方法 | 路径 | 返回 |
|------|------|------|
| GET | `/roi/summary` | 时间窗内：总 token、折算金额、按场景分布、按模型分布、失败率、平均延迟、配额水位 |
| GET | `/roi/trend?days=30` | 逐日：token（按场景堆叠）、金额、调用次数、失败数 |
| GET | `/roi/notes?window=30` | 笔记级 ROI 列表：note_id/标题/引用次数/索引成本/健康度分级，支持按 ROI 排序 |
| GET | `/roi/prompts` | 提示词级 ROI 列表：使用次数/质量分/优化投入/性价比排行 |
| GET | `/roi/scenes` | 场景四象限数据点：scene、成本、频次、评分 |

**服务层**：新建 `app/services/roi_service.py`，对齐 `StatsService` 风格：

- 金额换算在读取时做（单价可变，token 流水保持中立）；
- `citations` 解析复用 `app/schemas/common.py` 的 `decode_json_list`，脏数据跳过；
- 笔记健康度分级在 Python 端计算（阈值常量定义在 service 顶部，与 `TREND_DAYS` 等常量风格一致）；
- 时间窗参数白名单校验（7/30/90 天），防任意值扫全表。

**Schemas**：`app/schemas/roi.py` 定义响应模型（RoiSummary / RoiTrendPoint / NoteRoiItem / PromptRoiItem / SceneQuadrantPoint）。

---

## 6. 前端设计

### 6.1 页面结构

新增 `views/RoiDashboard.vue` 页面，路由加入 `router/index.ts` 与 NavBar。页面外壳用 `.rh-page`（列表型 1320px）。

```
┌──────────────────────────────────────────────┐
│ 顶部指标条：总成本｜本月 Token｜调用次数｜失败率     │
├──────────────────────────────────────────────┤
│ VizCard: 成本趋势（30天堆叠面积图，按场景）         │
│ VizCard: 场景成本占比（环形图）＋ 模型成本 TOP5       │
├──────────────────────────────────────────────┤
│ VizCard: 场景 ROI 四象限散点图                    │
├──────────────────────────────────────────────┤
│ VizCard: 知识资产健康度列表（高产出/沉睡/高耗）       │
│ VizCard: 提示词性价比排行（横向条形图）             │
└──────────────────────────────────────────────┘
```

### 6.2 实现要点（遵守项目设计规范）

- 图表统一走 `composables/useChart.ts` 按需引入 ECharts，读取 `--rh-*` 令牌配色，**禁止硬编码色值**；
- 图表卡片复用 `components/dashboard/VizCard.vue` 外壳；
- 每个图表附无障碍数据表（规范要求）；
- 金额格式：`¥0.00`（<0.01 显示 `<¥0.01`），token 用 `k/m` 缩写；日期用 `utils/format.ts`；
- 时间窗切换用 Element Plus `el-radio-group`（7/30/90 天），状态本地 `ref` 即可，无需 Pinia store；
- 空态：从未用过 AI 功能时展示 `EmptyState.vue` + 「去体验 AI 对话」引导，而不是空白图表。

---

## 7. 实施计划

| 阶段 | 内容 | 产出 |
|------|------|------|
| P1 数据层 | config 增加价格表；ai_usage_logs 加 prompt_id 列；Alembic 迁移；`usage.record_usage` 在 eval/optimize 场景传入 prompt_id | schema + 配置就绪 |
| P2 聚合层 | `roi_service.py` + `schemas/roi.py` + `routers/roi.py`，5 个接口 | 可用 API |
| P3 测试 | `tests/` 增加 ROI 聚合回归（沿用临时 SQLite 模式，构造 citations/usage/eval 数据断言分级与换算正确） | `uv run pytest` 全绿 |
| P4 前端 | RoiDashboard 页面 + 5 个图表模块 + 路由/导航接入 | 可视化看板 |
| P5 打磨 | 空态/加载（LoadingState 骨架屏）/错误态；深色主题适配自检；`npm run build` 验证 | 交付 |

> P1–P2 完成后即可用接口演示「数据闭环」，P4 完成后可整页演示。建议按 P1→P5 顺序串行提交，每阶段独立可回退。

---

## 8. 边界与风险

| 风险 | 对策 |
|------|------|
| 价格配置缺失导致金额失真 | 未定价模型显示「未计价」，金额仅汇总已定价部分并标注 |
| citations JSON 脏数据/旧数据无 note_id | 解析失败跳过该条（对齐 stats_service 的容错风格） |
| 引用次数 ≠ 真实价值（用户可能不用 AI 问笔记） | 看板文案明确「ROI 基于AI 使用行为衡量」，沉睡资产是「建议」不是「判决」 |
| MySQL 5.7 无窗口函数 | 全部聚合用 Python 端处理（与 stats_service 同策略），不用 SQL 窗口函数 |
| 时间窗过大查询慢 | 时间窗白名单（7/30/90），且 `ix_ai_usage_user_created` 已有索引支撑 |
| 多用户数据隔离 | 所有查询强制 `user_id == current_user.id`，与现有路由一致 |

---

## 9. 为什么这是比赛加分项（评审视角）

1. **数据闭环完整**：计量 → 聚合 → 换算 → 可视化 → 反哺用户决策（清理沉睡笔记、优化贵提示词），不是摆设图表；
2. **ROI 可证实**：收益用「AI 引用次数」「评测提分」这类可复现数据，而非拍脑袋的价值估计；
3. **行业稀缺**：主流笔记/AI 产品几乎没有「知识资产 ROI」视角，属于差异化创新；
4. **复用度高**：99% 基于已落库数据，改动小、演示稳，比赛现场不易翻车。

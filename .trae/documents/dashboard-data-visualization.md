# Dashboard 数据可视化（功能 C）

## Context（背景与目标）

当前 [Dashboard.vue](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Dashboard.vue) 只有"最近笔记列表 + 常用提示词列表 + 3 个静态数字"，没有任何图表；前端也未安装任何图表库。用户希望把工作台升级为**数据可视化面板**，让"知识资产"以图形方式直观呈现，契合极简黑白高端审美与竞赛展示效果。

目标产出：4 个可视化模块 —— ① 标签云 ② 近 30 天创作趋势折线 ③ 笔记分类分布环形图 ④ 提示词使用日历热力图。

**关键约束**：
- 全部数据来自现有列，**无需新建表、无需 Alembic 迁移**（note.tags/created_at/category_id、prompt.usage_count、prompt_usage_logs.used_at）。
- 后端分层沿用 Router→Service→ORM；响应用 `success_response`；前端 http 拦截器自动解包 `data`。
- 日期聚合在 **Python 端分桶**（不用 MySQL 专有日期函数），保证 SQLite 开发库与 MySQL 生产库行为一致。
- 图表库选 **ECharts**（按需引入 + wordcloud 插件），Three.js 场景封装为 composable 并 **dispose 释放内存**（用户规范）。

---

## 一、后端：新增统计接口

### 1. `backend/app/services/stats_service.py`（新建）
`StatsService.get_overview(db, user_id) -> dict`，一次返回全部聚合数据：

- **标签云 `tag_cloud`**：取该用户所有 note 与 prompt 的 `tags` 列（JSON 数组字符串），用 `schemas/common.py` 的 `decode_json_list` 解码后按标签计数，输出 `[{name, value}]`（按 value 降序，截断前 ~60 个）。
- **创作趋势 `creation_trend`**：近 30 天，按 `created_at` 在 Python 端逐日分桶，输出 `[{date:'YYYY-MM-DD', notes, prompts}]`（30 个点，缺失日补 0）。
- **分类分布 `category_distribution`**：note 按 `category_id` 分组，回溯 `parent_id` 到**一级分类**（根祖先）再聚合；`category_id` 为空归入"未分类"。复用 `CategoryService` 思路，取全量 note 类型分类构建 `{id: parent_id}` 映射。输出 `[{name, value}]`。
- **使用热力图 `usage_heatmap`**：近 ~120 天 `PromptUsageLog.used_at` 按日计数，输出 `[{date:'YYYY-MM-DD', count}]`。

> 计数规模是个人工具级（几十~几百行），全表扫描 + Python 聚合足够，无需 SQL 优化。

### 2. `backend/app/routers/stats.py`（新建）
```
router = APIRouter(tags=["统计"])
service = StatsService()

@router.get("/overview")
async def overview(db=Depends(get_db), current_user=Depends(get_current_user)):
    return success_response(data=await service.get_overview(db, current_user.id), msg="获取统计成功")
```

### 3. `backend/main.py`（改）
仿现有注册：`from app.routers import ... stats` + `app.include_router(stats.router, prefix="/api/stats", tags=["统计"])`。

### 4. `backend/tests/`（改）
新增 1 个用例：登录用户后 `GET /api/stats/overview` 返回 200，且 `data` 含 `tag_cloud / creation_trend / category_distribution / usage_heatmap` 四个键（结构契约锁定，复用现有 TestClient + 临时 SQLite 套件）。

---

## 二、前端：ECharts 封装 + 4 个图表组件

### 1. 依赖安装
`frontend/`：`npm i echarts` 与 `npm i echarts-wordcloud`（标签云插件）。

### 2. `frontend/src/api/stats.ts`（新建）
定义 `StatsOverview` 类型（对应后端四段数据）+ `statsApi.overview(): Promise<StatsOverview>`（`http.get('/stats/overview')`）。禁止 any，字段严格类型化。

### 3. `frontend/src/composables/useChart.ts`（新建，符合"Three.js/可视化封装为 composable + dispose"规范）
通用 ECharts 挂载 composable：
- 入参：`elRef`、`optionFactory`（或响应式 option）
- 内部：`onMounted` 用 `echarts.init` 创建实例（按需 `import * as echarts from 'echarts'` + 引入所需组件；wordcloud 单独 import 插件）；`ResizeObserver` 自适应容器宽；`watch` option 变化 `setOption`；**`onUnmounted` 调 `chart.dispose()` + 断开 observer**，杜绝内存泄漏。
- 统一黑白主题常量（`#000 / #fff / #F5F5F5 / #2563EB`）与 `grid/tooltip` 基础配置，供各图复用。

### 4. `frontend/src/components/dashboard/`（新建 4 个组件）
每个组件 `<script setup>` + 调用 `useChart`，接收 props 数据，渲染一个 ECharts 容器：
- `TagCloud.vue` — wordcloud 系列；字号/颜色映射热度；点击标签 → `router.push('/notes')` 前调 `notesStore.setSearch(tag)`（Pinia 全局态跨路由保留）。
- `CreationTrend.vue` — 双折线（笔记/提示词），近 30 天，X 轴日期。
- `CategoryDonut.vue` — 环形 pie（`radius:['45%','70%']`）+ 图例。
- `UsageHeatmap.vue` — `visualMap` + `calendar` 坐标系热力图，近 ~120 天。

### 5. `frontend/src/views/Dashboard.vue`（改）
- `onMounted` 并行 `statsApi.overview()` 拉一次统计（与现有 notes/prompts 拉取并存；失败不阻塞页面，图表区显示空态）。
- 在现有 `content-grid` 下方新增 `<section class="viz-grid">`：响应式 2×2 网格（`@media` 窄屏转单列），放置 4 个图表组件，风格沿用现有 `.panel` 边框/圆角/`--rh-*` 变量。
- 保持既有欢迎区/搜索条/最近工作/常用提示词不动（scope 到"新增可视化"）。

---

## 三、验证方式

1. **后端**：`cd backend && uv run pytest -v`（含新增 stats 用例，临时 SQLite 无需起服务）。
2. **前端构建**：`cd frontend && npm run build`（vue-tsc 类型检查 + vite 打包通过）。
3. **浏览器端到端**（前后端已运行：后端 8800 / 前端 5173）：
   - 用现有账号登录进 `/dashboard`；
   - 确认 4 个图表渲染：标签云字号分层、趋势双折线、环形图图例、热力图日历；
   - 点击标签云某标签 → 跳转笔记页并按该标签过滤；
   - 控制台无报错；切窄屏验证响应式换行。
   - 造数据用临时脚本（验证后删除、清理测试用户，沿用上次做法）。

---

## 四、影响文件清单

| 文件 | 动作 |
|---|---|
| `backend/app/services/stats_service.py` | 新建 |
| `backend/app/routers/stats.py` | 新建 |
| `backend/main.py` | 改（注册路由） |
| `backend/tests/test_api.py`（或套件内） | 改（+1 用例） |
| `frontend/package.json` | 改（+echarts, echarts-wordcloud） |
| `frontend/src/api/stats.ts` | 新建 |
| `frontend/src/composables/useChart.ts` | 新建 |
| `frontend/src/components/dashboard/{TagCloud,CreationTrend,CategoryDonut,UsageHeatmap}.vue` | 新建 |
| `frontend/src/views/Dashboard.vue` | 改（拉数据 + viz-grid 区） |

**无需数据库迁移。** 全部为读聚合 + 前端展示。

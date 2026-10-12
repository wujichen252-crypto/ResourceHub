# 方案：资源广场笔记「点赞 + 收藏」与主页查看

## Context

用户希望为笔记新增点赞、收藏功能模块，并在主页（Dashboard）能查看自己收藏和点赞的笔记。经确认的需求边界：

- 点赞/收藏是**社交行为**，仅针对**资源广场公开笔记**（`visibility='public'` 的 Note），不能对自己的笔记点赞/收藏
- 广场列表卡片与独立详情页（`/plaza/note/:id`）显示点赞数/收藏数，并提供当前用户的切换按钮
- Dashboard 新增「我的收藏」「我的点赞」两个区块，点击直达广场详情页
- 提示词本期不做（仅笔记）
- 与现有 fork（复制副本）语义区分：收藏是只读书签，不复制内容

## 一、数据模型

新建 `backend/app/models/note_reaction.py`，两张同构表 `NoteLike`(note_likes) / `NoteFavorite`(note_favorites)：

| 列 | 类型 |
|---|---|
| id | Integer PK |
| note_id | Integer FK→notes.id, ondelete=CASCADE, NOT NULL |
| user_id | Integer FK→users.id, ondelete=CASCADE, NOT NULL |
| created_at | DateTime, server_default=now() |

约束/索引：
- `UniqueConstraint(note_id, user_id)` — 防重复（并发兜底）
- `Index(user_id, created_at)` — 支撑「我的列表」分页排序
- 不存冗余计数字段，计数一律查询时 `COUNT(*)` 派生（无漂移）

FK 决策说明：广场 fork 溯源字段故意无 FK（历史凭证需活过删除），但点赞/收藏是实时状态，CASCADE 清理正是期望语义。取消发布不删行——重新发布后历史点赞恢复。

在 `backend/app/models/__init__.py` 注册两个新模型。

**迁移**：`uv run alembic revision --autogenerate -m "add_note_like_favorite_tables"`（down_revision 应为 head `2c85a155f6a9`），人工核对后 `uv run alembic upgrade head`。

## 二、后端 API

错误码：`backend/app/core/errors.py` 新增 `CANNOT_REACT_OWN_NOTE = 6001`（"不能点赞或收藏自己的笔记"）。

服务层新建 `backend/app/services/plaza_reaction_service.py`（PlazaReactionService），路由加在现有 `backend/app/routers/plaza.py`：

| 端点 | 说明 | data |
|---|---|---|
| `PUT /api/plaza/note/{note_id}/like` | toggle 点赞 | `{liked, like_count}` |
| `PUT /api/plaza/note/{note_id}/favorite` | toggle 收藏 | `{favorited, favorite_count}` |
| `GET /api/plaza/favorites` | 我的收藏列表（page/page_size） | PlazaListResponse 同形 |
| `GET /api/plaza/likes` | 我的点赞列表 | 同上 |

toggle 逻辑：① 笔记不存在或非 public → 5001；② `note.user_id == current_user.id` → 6001；③ 有行 DELETE / 无行 INSERT，捕获 IntegrityError 视为已存在；④ 返回 COUNT 新值。

**列表/详情聚合防 N+1**：新增 `enrich(db, note_ids, user_id)` 后置批量查询——每页至多 4 条 SQL（like/favorite 各一条 `IN + GROUP BY` 计数、一条 `IN + user_id` 得已操作集合），不 JOIN 进主查询（保护现有 `count_query = select(func.count()).select_from(query.subquery())` 结构）。

改造 `backend/app/routers/plaza.py`：
- `_item_out()` 加可选 `reaction` 参数，merge `like_count/favorite_count/liked/favorited`
- `list_items` / `get_item` / `list_mine` 收集 note id 后调一次 enrich；prompt 类型跳过取默认值
- 新增上述 4 端点

**schemas**（`backend/app/schemas/plaza.py`）：`PlazaItemResponse` 与 `PlazaDetailResponse` 各加 4 字段，默认 `0/False`（prompt 行序列化不报错）。

**我的列表查询**：join Note（仍 public 才出现）+ User（作者信息），按 reaction 表 `created_at` 倒序分页；item 复用 PlazaItemResponse 序列化。

## 三、前端

| 文件 | 改动 |
|---|---|
| `frontend/src/api/plaza.ts` | PlazaItem/PlazaDetail 接口加 4 字段；新增 `toggleLike/toggleFavorite/favorites/likes` 方法 |
| `frontend/src/stores/plaza.ts` | `toggleLike/toggleFavorite`：调 API 后按返回值就地更新 `items` 中对应项（不整页 refetch） |
| `frontend/src/views/Plaza.vue` | 卡片 footer 复制按钮左侧加点赞/收藏按钮（text 型 + 计数，仅 `type==='note'` 渲染，`@click.stop`），激活态实心图标+强调色 |
| `frontend/src/views/PlazaDetail.vue` | meta 行加同样两个切换按钮，绑定 `detail.liked/like_count`，点击回写 detail |
| `frontend/src/views/Dashboard.vue` | 新增一个 section：两列区块「广场收藏」「广场点赞」（文案与提示词收藏指标区分），各拉前 4 条；行内显示标题+作者+时间，点击 `router.push('/plaza/note/'+id)`；空态引导去广场；onMounted 并行拉取、失败静默 |

路由无需新增（`/plaza/:type/:id` 已覆盖）。

## 四、测试

新建 `backend/tests/test_plaza_reaction.py`（复用 conftest 的 `client`/`register_user`/`auth` fixture）：

1. toggle 契约：点赞→liked=true,count=1；再 toggle→false,0；like 与 favorite 互不影响
2. 自己点赞/收藏自己 → 400 + code 6001
3. 对 private/不存在笔记 toggle → 404 + code 5001
4. 列表 enrich：多人点赞后 like_count 正确、各视角 liked/favorited 正确；prompt 项为默认值
5. 详情 enrich 各视角正确
6. `/plaza/favorites`、`/plaza/likes`：仅自己的、仍 public 的，时间倒序，分页 total 正确；作者取消发布后从他人列表消失
7. 回归：现有 42 用例全绿（`_item_out` 签名变更处同步）

## 五、实施顺序

1. 模型 + `__init__.py` 注册 + errors.py 6001
2. Alembic autogenerate → 人工核对 → upgrade head（远端 MySQL）
3. plaza_reaction_service.py
4. schemas/plaza.py + routers/plaza.py（4 端点 + enrich 接线）
5. pytest 新用例 + 全量回归
6. 前端 api → store → Plaza.vue → PlazaDetail.vue → Dashboard.vue
7. `npm run build` + 浏览器端到端验证（探针账号双账号：A 发布、B 点赞收藏、B Dashboard 查看、跳转、取消 toggle、清理）
8. 重启后端实例（当前 8800 无 --reload）

## 六、风险与对策

- 自赞校验基于 DB 的 `note.user_id`，不信任前端隐藏
- 并发 toggle：唯一索引兜底 + IntegrityError 捕获
- prompt 类型字段默认值双保险（后端默认 + 前端按 type 隐藏）
- autogenerate 可能带无关漂移，生成后逐行 review
- Dashboard 现有"收藏数"指标是提示词收藏，新区块文案明确"广场收藏/广场点赞"避免混淆

## 验证清单

- `uv run pytest -v`（backend）全绿
- `npm run build`（frontend）通过
- 浏览器：广场卡片 toggle 按钮计数即时变化；详情页按钮状态与 Dashboard 区块一致；Dashboard 点击跳转 `/plaza/note/:id`；取消发布后收藏列表消失

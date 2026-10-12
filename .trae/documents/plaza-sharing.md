# 资源广场（笔记/提示词分享）实施方案

## Context

ResourceHub 目前是纯个人工具，无任何内容共享能力。用户希望扩展"分享"功能：把笔记或提示词发布到组织/团队内公开可见。经确认的产品决策：

- **形态**：站内公开广场（所有注册用户互相可见）
- **范围**：笔记 + 提示词都可发布
- **权限**：他人只读浏览 + 一键复制（fork）为自己的副本，副本与原作者脱离但保留"来自 @xxx"署名；发布者可随时取消发布

现状核实：Note/Prompt 模型无 visibility 字段；全库无 share 相关代码；Alembic 就绪（`backend/migrations/`，基线 revision `b3e21b6acf8f`）；错误码分段 note=2xxx / prompt=4xxx，广场用新段 5xxx。

## 一、数据模型（原表加列，不建 shares 表）

`backend/app/models/note.py` 和 `prompt.py` 对称新增：

| 列 | 类型 | 说明 |
|---|---|---|
| `visibility` | String(20)，NOT NULL，server_default="private" | private / public |
| `published_at` | DateTime，NULL | 发布时间 |
| `source_user_id` | Integer，NULL，**无外键** | fork 溯源：原作者 id |
| `source_content_id` | Integer，NULL，无外键 | fork 溯源：原内容 id |
| `source_username` | String(50)，NULL | 署名快照（"来自 @xxx"） |

- 溯源列故意不建 FK：notes/prompts.user_id 是 CASCADE，若溯源带 FK，原作者删号会误删 fork 副本
- 广场查询加复合索引 `(visibility, updated_at)`
- MySQL 5.7 兼容：沿用现有 String 存 JSON 的 tags/variables 模式，无原生 JSON 函数

### Alembic 迁移

```bash
cd backend
uv run alembic current   # 确认远端库在 b3e21b6acf8f
uv run alembic revision --autogenerate -m "add_plaza_visibility_and_fork_columns"
uv run alembic upgrade head
```
autogenerate 连 .env 远端 MySQL；生成后人工检查 diff 只含新列/新索引。

## 二、后端 API

新文件 `backend/app/routers/plaza.py`（prefix `/api/plaza`，main.py include_router），`backend/app/services/plaza_service.py`，`backend/app/schemas/plaza.py`。

| 端点 | 说明 |
|---|---|
| `PUT /publish` | body `{type:"note"|"prompt", id}`，归属校验后置 public + published_at |
| `PUT /unpublish` | 置回 private |
| `GET /items?type=&search=&tag=&page=&page_size=` | 广场列表（需登录），join User 返回 author_username/avatar；type 必选其一（与 UI Tab 一致，避免跨表合并分页） |
| `GET /items/{type}/{id}` | 广场详情，仅 public 可读，否则 5001 |
| `POST /fork` | body `{type, id}`，返回新副本 id |
| `GET /mine` | 我发布的内容（管理用） |

错误码（`backend/app/core/errors.py` 新增）：`PLAZA_ITEM_NOT_FOUND=5001`、`INVALID_CONTENT_TYPE=5002`。

### Service 要点

- 列表：`select(Note, User.username, User.avatar).join(User).where(Note.visibility=='public')`，search 走 title/content ilike（复用 note_service 模式）
- fork：新建行归当前用户；content/description/tags/variables 原样复制；`category_id=None`（归未分类）；`is_pinned/is_favorite=False`、`usage_count=0`；写三个 source 溯源字段；不复制版本历史/预设/使用日志
- publish/unpublish 非 owner → 403

## 三、前端

| 文件 | 改动 |
|---|---|
| `frontend/src/api/plaza.ts` | 新建：类型 + 6 方法（http 拦截器已解包） |
| `frontend/src/stores/plaza.ts` | 新建：仿 stores/notes.ts（items/total/page/filters/fetchItems/fork） |
| `frontend/src/views/Plaza.vue` | 新建：类型 Tab（笔记/提示词）+ 搜索 + 卡片流（作者署名/头像、tags、fork 按钮），沿用 --rh-* 主题与 stagger 动画 |
| `frontend/src/router/index.ts` | 加 `/plaza` 懒加载路由（requiresAuth） |
| `frontend/src/components/NavBar.vue` | 工作区分组加"资源广场"入口 |
| `frontend/src/views/Prompts/PromptDetail.vue` | 操作区加"发布到广场/取消发布"（仅 owner 可见） |
| `frontend/src/components/notes/NoteContent.vue` | 操作区加同款按钮 |
| `frontend/src/api/notes.ts` / `prompts.ts` | Note/Prompt 接口补 visibility 等字段 |

fork 交互：卡片按钮 → ElMessageBox 确认 → plazaApi.fork → ElMessage "已复制到你的库，来自 @xxx"。

## 四、测试（backend/tests/test_plaza.py，双用户 alice/bob）

1. 契约：publish 后广场列表含该条且带 author_username；unpublish 后消失
2. 权限：bob 对 alice 私有内容详情 5001；bob publish alice 笔记 403
3. 隔离：未发布内容不出现在广场
4. fork 正确性：副本 category_id=None、tags 相等、usage_count=0、source_username=alice；原作者删除后副本仍在
5. 参数：type 非法 5002；search/分页过滤

## 五、实施顺序

1. models 加列 → 2. alembic 迁移（远端） → 3. errors.py 错误码 → 4. schemas/plaza.py → 5. plaza_service.py → 6. plaza.py 路由 + main.py 注册 → 7. test_plaza.py 跑绿 → 8. api/plaza.ts + stores/plaza.ts → 9. Plaza.vue + 路由 + NavBar → 10. 发布按钮 + fork 入口 → 11. 验证

## 六、验证方式

- `uv run pytest tests/ -q` 全绿
- `npm run build` 通过
- 浏览器端到端：双账号（A 发布 → B 广场可见 → B fork → B 库中出现副本带署名 → A 取消发布 → B 广场不再显示），验证后清理测试账号
- 注意：当前 8800 由无 --reload 的后台实例占用，后端代码改完需重启该实例

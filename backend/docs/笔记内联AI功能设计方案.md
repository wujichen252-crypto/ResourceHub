# 笔记内联 AI（选中文本 → 解释 / 改写 / 提问 → 插入笔记）设计方案

> 版本：v1.0（2026-11-05）
> 状态：待实现
> 关联模块：笔记（Notes）、AI 能力层（/api/ai）

## 一、功能概述

在笔记编辑器中选中一段文本后，浮出内联 AI 菜单，提供三种操作：

| 动作 | 英文标识 | 语义 | 结果去向 |
|---|---|---|---|
| 解释 | `explain` | 对选中文本做背景解释、概念拆解 | 结果以「引用块 + 原文」形式插入到选区**下方** |
| 改写 | `rewrite` | 润色 / 精简 / 扩写选中文本（可带附加要求） | 结果**替换**选区原文 |
| 提问 | `ask` | 以选中文本为上下文，回答用户的追加问题 | 以「问 + 答」块插入到选区**下方** |

三种动作的结果都经用户确认后才写入笔记（先预览，点「插入」才落编辑器），写入后沿用现有自动保存链路（`markDirty → 1500ms 防抖 → PUT /api/notes/{id}`），RAG 索引由后端 `index_note_in_background` 自动重建，无需额外处理。

MVP 范围限定：**仅编辑态（WysiwygEditor）支持**；阅读态（NoteReader）划词为二期。

## 二、总体交互流程

```
用户选中文本（Tiptap selection 非空且非纯空格）
   → 浮出内联 AI 菜单（跟随选区位置，层级 --rh-z-popover）
   → 用户点「解释 / 改写 / 提问」（改写可展开附加要求输入框）
   → 菜单收起，浮层显示结果卡片（loading 骨架 → 流式/非流式正文）
   → 卡片底部三个按钮：
       [插入]   explain/ask → insertContentAt 选区末尾之后
                rewrite     → 替换选区
       [复制]   写入剪贴板，不落笔记
       [重试/关闭]
   → 插入后触发自动保存
```

## 三、与现有架构的复用清单

### 后端可直接复用

| 能力 | 位置 | 用法 |
|---|---|---|
| LLM 调用（非流式） | `services/ai/provider.py` `OpenAICompatibleProvider.chat()` | 短文本处理，非流式足够；用 `get_chat_provider()` 工厂 |
| 轻量模型 | `settings.AI_FAST_MODEL` | 内联动作属于轻量任务，走 fast model 控成本 |
| 配额 | `services/ai/usage.py` `ensure_quota()` / `record_usage()` | 新增 `scene="inline"` |
| 安全护栏 | `services/ai/safety.py` `SYSTEM_GUARD` | 作为 system 消息前缀 |
| 错误码 | `core/config` 7001（未配置）/ 7003（超配额） | 沿用 `APIError(ErrorCode.AI_*)` |
| 认证 | `core/deps.py get_current_user` | 同现有 ai.py 全部端点 |

### 前端可直接复用

| 能力 | 位置 | 用法 |
|---|---|---|
| axios 底座 | `api/http.ts`（`/api` 前缀、Authorization 注入、401 刷新、`{code,data,msg}` 解包） | 内联请求为非流式，直接走 axios 实例 |
| markdown 渲染 | 各组件已有的 `md`（markdown-it）实例 | AI 输出为 Markdown，转 HTML 后交给 Tiptap |
| AI 专属配色 | `theme.css` `--rh-ai / --rh-ai-strong / --rh-on-ai` | 菜单与结果卡片的视觉语言 |
| 浮层层级 | `--rh-z-popover` | 浮层 z-index |
| 状态骨架 | `components/common/LoadingState.vue` | 结果卡片 loading 态（禁止转圈图标） |

### 需要新写的部分

- 后端：`services/ai/inline_service.py`、`schemas/ai.py` 增量 schema、`routers/ai.py` 一个端点
- 前端：`WysiwygEditor.vue` 增加选区监听与暴露 API、新组件 `InlineAIMenu.vue` / `InlineAIResult.vue`、`api/ai.ts` 一个方法

## 四、API 设计

### `POST /api/ai/note/inline`

**认证**：`Depends(get_current_user)`；**非流式**（见下文「为什么不用 SSE」）。

请求体（加入 `app/schemas/ai.py`）：

```python
class InlineAction(str, Enum):
    EXPLAIN = "explain"
    REWRITE = "rewrite"
    ASK = "ask"

class InlineAIRequest(BaseModel):
    action: InlineAction                      # 动作类型
    text: str = Field(min_length=1, max_length=2000)   # 选中的原文（纯文本）
    instruction: str = Field(default="", max_length=500)  # 改写附加要求 / 提问的问题
    note_title: str = Field(default="", max_length=255)   # 笔记标题，供模型理解语境
    context_before: str = Field(default="", max_length=600)  # 选区前文（纯文本截断）
    context_after: str = Field(default="", max_length=600)   # 选区后文（纯文本截断）
```

响应体：

```python
class InlineAIResponse(BaseModel):
    action: InlineAction
    result: str        # AI 输出（Markdown 纯文本，不带围栏代码块包裹正文）
    model: str         # 实际使用的模型名
    tokens: int        # 本次消耗总 token
```

**错误**：7001 未配置 AI（`_ensure_ai_ready()`）、7003 当日配额超限、422 参数校验（`text` 超长等）、超时 → provider 抛 `AIProviderError` 转 502 语义的 `APIError`。

**为什么不用 SSE**：
1. 输出短（解释/改写约 100~600 字），流式收益有限；
2. 结果卡片需要「确认后插入」的二次交互，流式期间浮层内排版抖动且插入语义不明确；
3. 复用 axios 的统一错误处理（401 刷新、超时、`{code,data,msg}` 解包），比 fetch 手工 SSE 简单一档。
二期若要做长文续写，再加 `POST /api/ai/note/inline/stream`（SSE，复用 `useSSE`），事件协议沿用 `meta/token/done/error`。

## 五、Prompt 设计

服务内定义三段 system 模板（`inline_service.py` 常量），统一前缀 `SYSTEM_GUARD`：

```
# 公共部分（拼在 SYSTEM_GUARD 之后）
你是笔记编辑器内的写作助手。用户的笔记标题为「{note_title}」。
下面是选中文本的上下文（仅作理解用，不要输出）：
【前文】{context_before}
【选中文本】{text}
【后文】{context_after}
```

- **explain**：`解释【选中文本】。要求：1) 用中文，Markdown 格式；2) 先一句话定义，再分点展开要点；3) 控制在 300 字以内；4) 不要复述原文。`
- **rewrite**：`改写【选中文本】{instruction}。要求：1) 只输出改写后的文本，不要任何说明；2) 保持原文语言与 Markdown 行内格式；3) 长度与原文相当（除非用户另有要求）。instruction 为空时默认指令为「润色，使表达更清晰流畅」。`
- **ask**：`基于【选中文本】及上下文回答用户问题：{instruction}。要求：1) 用中文 Markdown；2) 与选中文本直接相关；3) 控制在 400 字以内。`

参数：`temperature` explain/ask=0.3，rewrite=0.5；`max_tokens=800`；model=`settings.AI_FAST_MODEL`。

调用：`provider.chat(messages, model=..., temperature=..., max_tokens=800)`，`ChatResult.text` 去除首尾空白后返回。**不落 ai_messages 表**（内联是对笔记的编辑辅助，不是会话），仅 `record_usage(db, user.id, scene="inline", ...)`。

## 六、后端实现清单

| 文件 | 改动 |
|---|---|
| `app/schemas/ai.py` | 新增 `InlineAction` / `InlineAIRequest` / `InlineAIResponse` |
| `app/services/ai/inline_service.py` | **新文件**：`class InlineService`，方法 `async def run(db, user, request: InlineAIRequest) -> InlineAIResponse`。内部：`ensure_quota(db, user.id)` → 拼 messages → `get_chat_provider().chat(...)` → `record_usage(..., scene="inline")` → 返回 |
| `app/routers/ai.py` | 新增 `POST /note/inline` 端点（放 `/eval` 之前即可），复用 `SSE_HEADERS` 之外的普通 `success_response` |
| `tests/` | 新增 `tests/test_inline_ai.py`：mock provider，覆盖三种 action 的 prompt 拼装、text 超长 422、未配置 7001 |

伪代码（`inline_service.py` 核心）：

```python
class InlineService:
    async def run(self, db, user, req) -> InlineAIResponse:
        ensure_quota(db, user.id)                       # 7003
        messages = self._build_messages(req)            # SYSTEM_GUARD + 场景指令
        provider = get_chat_provider()                  # 7001
        result = await provider.chat(messages, model=settings.AI_FAST_MODEL,
                                     temperature=..., max_tokens=800)
        await record_usage(db, user.id, "inline", settings.AI_FAST_MODEL, result.usage)
        return InlineAIResponse(action=req.action, result=result.text.strip(),
                                model=settings.AI_FAST_MODEL, tokens=result.usage.total_tokens)
```

## 七、前端实现清单

### 7.1 `WysiwygEditor.vue` 改造（核心）

1. **选区监听**：`useEditor({ ..., onSelectionUpdate({ editor }) {...} })`，将 `{ hasSelection, selectionText, selectionRect, isEmptySelection }` 存入 ref 并 `emit('selection-change', ...)`。判定规则：`editor.state.selection` 非空 + `selectionText.trim()` 非空；`selectionRect` 取 `window.getSelection().getRangeAt(0).getBoundingClientRect()`（无需新增 Tiptap 扩展或 tippy 依赖）。
2. **暴露 API**（`defineExpose` 追加）：
   - `getInlineContext(): { text, context_before, context_after }` —— 选区纯文本 + 前后各取 600 字符（用 `editor.state.doc.textBetween`）；
   - `insertBelow(html: string)` —— `editor.chain().focus().insertContentAt(selection.to, html)`（解释/提问用）；
   - `replaceSelection(html: string)` —— `editor.chain().focus().insertContentAt(selection, html)`（改写用）。
   HTML 侧由调用方先把 AI 的 Markdown 用 `md.render` 转 HTML 并 `DOMPurify.sanitize`。
3. 工具栏不动；浮层组件由 `NoteContent.vue` 挂载（编辑器组件保持纯编辑职责）。

### 7.2 新组件

**`components/notes/InlineAIMenu.vue`**（气泡菜单）
- Props：`visible: boolean; rect: { top, left, width }`；Emits：`action(name: 'explain'|'rewrite'|'ask')`、`close`
- 定位：`position: fixed`，取选区 rect 顶部上方 8px（空间不足翻转到下方）；`z-index: var(--rh-z-popover)`
- 视觉：`--rh-ai` 色系按钮、`--rh-radius-sm`、按 `Esc` / 点击外部关闭
- 可访问性：`role="menu"`，按钮带 `aria-label`；「改写」旁提供附加要求小输入框（折叠展开）

**`components/notes/InlineAIResult.vue`**（结果卡片）
- Props：`action, loading, result, error`；Emits：`insert / copy / retry / close`
- loading 用 `LoadingState variant="detail"`（骨架屏）；结果区 Markdown 渲染进 `.rh-markdown`
- 「插入」按钮：改写态文案为「替换原文」，解释/提问态为「插入到下方」；破坏性提示不需要（可撤销 Ctrl+Z）

### 7.3 状态与数据流

建议**不新增 pinia store**：内联 AI 是短生命周期、局部于编辑器的状态，放进 `NoteContent.vue` 的 3~4 个 ref（`inlineVisible / inlineAction / inlineLoading / inlineResult`）即可，避免污染 `aiWorkspace` 的会话快照。

`api/ai.ts` 追加：

```ts
export interface InlineAIResult { action: string; result: string; model: string; tokens: number }
inlineAI(payload: { action: string; text: string; instruction?: string;
                    note_title?: string; context_before?: string; context_after?: string })
  : Promise<InlineAIResult>   // axios 实例，timeout 建议用 LONG_TASK_TIMEOUT
```

`NoteContent.vue` 的接线（伪代码）：

```ts
async function handleInlineAction(action, instruction) {
  const ctx = editorRef.value.getInlineContext()
  inlineLoading.value = true
  try {
    inlineResult.value = await aiApi.inlineAI({ action, instruction, note_title: editTitle.value, ...ctx })
  } catch (e) { inlineError.value = normalizeError(e) }  // 7001/7003/超时 → 中文提示
  finally { inlineLoading.value = false }
}
function handleInlineInsert() {
  const html = DOMPurify.sanitize(md.render(inlineResult.value.result))
  if (inlineAction.value === 'rewrite') editorRef.value.replaceSelection(html)
  else editorRef.value.insertBelow(html)          // 解释/提问附带原文引用块
  closeInline()                                    // 插入后 onUpdate → markDirty → 自动保存
}
```

插入模板（前端拼装）：
- explain：`<blockquote class="rh-ai-inline">` + 解释正文（块级，`data-source="inline-ai"` 标记）
- ask：问（原问题加粗）+ 答 两段
- rewrite：直接替换，无包裹

## 八、安全、计量与成本控制

1. **计量**：`scene="inline"` 写入 `ai_usage_logs`，复用每日配额 `AI_DAILY_TOKEN_QUOTA`；前端对 7003 展示「今日 AI 用量已达上限」。
2. **成本**：fast model + `max_tokens=800` + 单次输入上限（2000 选区 + 1200 上下文），单次成本可预期（约 3K token 内）。
3. **注入防护**：选中文本来自用户自己的笔记，风险低，但仍统一走 `SYSTEM_GUARD` 前缀；`context_*` 与 `text` 均由前端 `textBetween` 提取的**纯文本**（不含 HTML），不存在标签注入面。
4. **隐私**：不落 ai_messages，不留原文副本（仅 usage 计数）；后续如需审计，加配置开关再落库。

## 九、边界与异常

| 场景 | 处理 |
|---|---|
| 未选中 / 仅空白 | 菜单不弹出（`selectionText.trim()` 判空） |
| 选区在代码块内 | MVP 一视同仁（当纯文本）；二期对 codeBlock 选中给「解释代码」专属指令 |
| AI 未配置 | 后端 7001；前端 blocked 态文案「AI 未配置，请到设置中填写 API Key」，菜单按钮置灰 |
| 请求超时 | axios timeout 用 `LONG_TASK_TIMEOUT`；超时文案「AI 处理超时，请重试」 |
| 选区在浮层出现后变化 | 以发起请求时刻的选区为准，插入前校验 `editor.state.selection` 仍非空；为空则退化为 `insertContentAt(doc.content.size)` 追加到文末并提示 |
| 改写结果为空 | 结果卡片显示 EmptyState，「插入」禁用 |
| 连续操作 | 浮层单例，新动作覆盖上一结果；进行中请求用 AbortController 可选取消 |

## 十、实施顺序（可照做的 checklist）

1. 后端：`schemas/ai.py` 增量 schema → `services/ai/inline_service.py` → `routers/ai.py` 端点 → `pytest` 用例（mock provider）
2. 前端：`api/ai.ts` 加 `inlineAI()` → `WysiwygEditor.vue` 选区监听 + 三个 expose API → `InlineAIMenu.vue` → `InlineAIResult.vue` → `NoteContent.vue` 接线 → 手工冒烟（选中文本三动作 + 插入 + 自动保存 + RAG 重建）
3. 收尾：`Settings.vue` AI 说明文案补一句内联功能；`docs/ui-design-audit.md` 若有功能清单同步

验收标准：
- 选中 → 菜单在选区上方 8px 弹出，Esc/点击外部可关；
- 三种动作均可预览、可插入/替换/复制，插入后 1.5s 内自动保存成功；
- `ai_usage_logs` 出现 `scene="inline"` 记录；未配置 AI 时按钮置灰且给出引导文案；
- 浅色/深色主题下浮层对比度均达标（`--rh-ai` / `--rh-on-ai`）。

## 十一、二期扩展（不在本期）

- 阅读态（NoteReader）划词：DOM selection → 源码位置映射成本高，考虑「结果只读展示，不回写」
- SSE 流式版本（长文续写 / 摘要全文）
- 代码块专属「解释代码 / 补注释」动作
- 内联动作自定义（用户在设置里配置自己的动作 + 提示词模板，复用 `prompt_presets` 思路）
- 与 Agent 记忆联动：高频解释的概念沉淀为 `agent_memories(fact)`

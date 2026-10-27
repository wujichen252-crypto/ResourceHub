# ResourceHub 前端 UI 设计审查报告

> 审查角色：最严格的 UI 设计评审
> 审查范围：`frontend/src` 全量 22 个 Vue 组件 + 2 个样式文件 + `index.html`
> 结论基调：**这套 UI 不是"设计系统"，而是"把多套设计系统拼接在一起"。**核心问题不是某个页面难看不难看，而是令牌、栅格、间距、字号、颜色语义、交互范式都缺乏唯一事实来源（single source of truth）。

---

## 摘要：必须先修的 12 条（P0）

| # | 问题 | 影响 | 证据 |
|---|------|------|------|
| 1 | **10 个"幽灵令牌"被引用但从未定义**，样式静默失效 | 选中态看不见、代码块无底色、标题下划线消失、动效失效 | 见 [1.1](#11-p0幽灵令牌--未定义却被引用) |
| 2 | **主色 `#e85d3f` 上放白字，对比度仅 3.46:1**，全部主按钮不达 WCAG AA | 所有主按钮文字可读性不足 | [2.1](#21-实测对比度表最严重的部分) |
| 3 | **三级文字 `#8b9087` 于浅色底上 2.94:1**，却用于 10–13px 全部辅助文字 | 日期、提示、eyebrow、计数全部低于可读阈值 | [2.1](#21-实测对比度表最严重的部分) |
| 4 | **桌面端没有主题切换入口**，只有移动端顶栏有 | 桌面用户无法切换深浅色 | [6.1](#61-功能入口缺失) |
| 5 | **`⌘ K` / `N` 是假快捷键**，全项目只有 `Ctrl+S` 真实存在 | 承诺了做不到的事，用户按下去没反应 | [6.2](#62-虚假快捷键与假入口) |
| 6 | **搜索框其实是跳转按钮**，点击直接去 `/prompts`，不聚焦、不搜索 | 全站第一屏的主入口是骗人的 | [6.2](#62-虚假快捷键与假入口) |
| 7 | **编辑器手动 `outline: none`**，并额外关闭 focus 轮廓 | 键盘用户完全看不到焦点在哪 | [2.3](#23-焦点可见性被主动移除) |
| 8 | **右键菜单垄断了笔记/目录的编辑·置顶·删除**，鼠标专属 | 键盘与触屏用户无法触达核心操作 | [2.4](#24-键盘与触屏可达性) |
| 9 | **5 套不同的页面外壳**（padding / max-width / 栅格方案全不一样） | 页面切换时内容区尺寸跳动 | [3.1](#31-页面外壳五套并存) |
| 10 | **标题字体在同一产品里既用 Georgia 衬线又用无衬线加粗** | 视觉语言撕裂，首页与内页不像一个产品 | [3.3](#33-标题字体两套体系混用) |
| 11 | **硬编码颜色 20+ 处**，其中 `#10b981` / `#ef4444` / `#1c1917` 完全游离于设计系统之外 | 深色模式下代码块与背景几乎同色，绿/红第三套绿色系 | [1.4](#14-硬编码颜色游离于令牌体系之外) |
| 12 | **`transition: all` 全局滥用** + 悬停改变 padding/缩放的三种不同位移 | 动画抖动、掉帧，且鼠标移动时列表跳动 | [1.3](#13-动效体系混乱) |

---

## 一、设计系统层：令牌是坏的

### 1.1 （P0）幽灵令牌 —— 未定义却被引用

`theme.css` 只定义了 `--rh-bg-base/card/elevated/overlay/inset/hover/active`、`--rh-border/strong/faint/divider`、`--rh-radius-xs/sm/md`、`--rh-transition-fast/normal/spring`。

但代码里引用了**这些从未定义的令牌**。它们不会报错，只会让 CSS 声明整条失效（CSS 自定义属性无值 → 该属性被丢弃）：

| 幽灵令牌 | 引用位置 | 静默失效后的实际后果 |
|---|---|---|
| `--rh-bg-subtle` | [NoteReader.vue#L202](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteReader.vue#L202)、[#L231](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteReader.vue#L231)、[#L256](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteReader.vue#L256) | **行内代码块无底色**、引用块无底色、表头无底色 |
| | [WysiwygEditor.vue#L289](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/WysiwygEditor.vue#L289)、[#L307](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/WysiwygEditor.vue#L307)、[#L338](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/WysiwygEditor.vue#L338) | 编辑器内行内代码/引用/表头全部无底色 |
| | [UsageAnalyticsPanel.vue#L162](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/prompts/UsageAnalyticsPanel.vue#L162) | 用量条形图**轨道变成透明**，进度条失去参照 |
| `--rh-border-light` | [NoteReader.vue#L183](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteReader.vue#L183)、[WysiwygEditor.vue#L190](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/WysiwygEditor.vue#L190)、[VersionHistoryPanel.vue#L210](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/prompts/VersionHistoryPanel.vue#L210) | 正文 h1/h2 下划线消失、编辑器工具栏下边框消失、抽屉分栏线消失 |
| `--rh-primary-lighter` | [VersionHistoryPanel.vue#L229](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/prompts/VersionHistoryPanel.vue#L229)、[#L233](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/prompts/VersionHistoryPanel.vue#L233)、[#L247](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/prompts/VersionHistoryPanel.vue#L247) | **版本"当前/已选中"两个状态背景相同且都无底色 → 选中态完全不可见** |
| `--rh-bg-secondary` | [PlazaDetail.vue#L244](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/PlazaDetail.vue#L244) | 靠 `#f5f5f5` 硬编码兜底，深浅色主题下都不对 |
| `--rh-transition` | [NoteTree.vue#L416](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteTree.vue#L416)、[VersionHistoryPanel.vue#L218](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/prompts/VersionHistoryPanel.vue#L218) | 树节点悬停过渡、版本卡片悬停过渡完全失效 |

> **这是最严重的一类问题：它不是"不好看"，而是"看起来能用、实际状态是错的"。** 尤其 `--rh-primary-lighter` 让版本对比功能的选择反馈归零。

### 1.2 （P1）令牌覆盖面严重不足

`theme.css` 有颜色、间距、圆角、时长，但**完全没有**：

- **字号令牌**（无 `--rh-font-size-*`）→ 全站字号硬编码 11/12/12.5/13/13.5/14/15/15.5/16/17/18/20/22/24/26/30/32/36/48px，**17 个不同字号**，无阶梯
- **字重令牌**（无 `--rh-font-weight-*`）→ 400/500/600/700/800 混用，同一层级语义下不统一
- **行高令牌** → 1.5/1.6/1.7/1.85 混用
- **层级（z-index）令牌** → 硬编码 `100 / 109 / 110 / 9999`（[NavBar](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/NavBar.vue#L80)、[NoteTree](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteTree.vue#L442)、[NoteContent](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteContent.vue#L629)）
- **圆角 `lg`/`xl` 档位** → 只有 xs/sm/md，导致所有"大圆角"需求都去硬编码（10px/12px）

同时 **`--rh-space-*` 定义了 8 档却几乎不用**：`24px / 32px / 44px / 52px / 70px / 84px / 100px / 480px` 等直接写死。令牌存在但不使用 = 令牌形同虚设。

### 1.3 （P1）动效体系混乱

1. **`--rh-transition-all-*` 用 `all` 作为过渡属性**（[theme.css#L14](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/styles/theme.css#L14)），并被 `.el-card / .el-button / .el-input__wrapper / .nav-link` 大量使用。`transition: all` 会监听元素全部可动画属性（含 width/height/padding/box-shadow），是明确的性能反模式，也是上面"悬停跳动"的根因之一。
2. **悬停位移三种写法并存**，同一"卡片可点"语义给出三种不同物理反馈：
   - 列表行：`padding-left/right` 从 0 变 7px（[Dashboard.vue#L60](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Dashboard.vue#L60)）→ **鼠标扫过时文字横向抖动**
   - 广场卡片：`translateY(-2px)`（[Plaza.vue#L213](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Plaza.vue#L213)）
   - 提示词卡片：`scale(1.015)`（[PromptList.vue#L364](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Prompts/PromptList.vue#L364)）
3. **入场动画分层级过多**：全局 `stagger-0…5` + PromptList 又自定义 `stagger-0…7`，同一套效果两套实现、两套延迟（60ms vs 40ms 步进）。

### 1.4 （P1）硬编码颜色游离于令牌体系之外

| 颜色 | 位置 | 问题 |
|---|---|---|
| `#1c1917`（近黑） | [NoteReader.vue#L211](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteReader.vue#L211)、[PlazaDetail.vue#L310](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/PlazaDetail.vue#L310) | **深色模式背景是 `#181a18`，代码块 `#1c1917` 与之几乎同色 → 代码块"消失"**；且与 [WysiwygEditor 的代码块用 `--rh-bg-inset`](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/WysiwygEditor.vue#L278) 不一致，**同一产品里代码块有 3 种外观**（阅读态近黑 / 编辑态米灰 / 广场态近黑+另一个内边距） |
| `#e7e5e4` | NoteReader / PlazaDetail | 深色代码块文字色写死，浅色主题下也强行近白 |
| `#10b981`（Emerald） | [VersionHistoryPanel.vue#L260](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/prompts/VersionHistoryPanel.vue#L260)、[#L364](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/prompts/VersionHistoryPanel.vue#L364)、[WysiwygEditor.vue#L361](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/WysiwygEditor.vue#L361) | **设计系统里的"成功色"是 `--rh-success #3f8f6b`，但全站"成功"实际用的是 `#10b981`**：出现第三套绿色 |
| `#ecfdf5` / `#fef2f2` / `#ef4444` | [VersionHistoryPanel.vue#L359-L373](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/prompts/VersionHistoryPanel.vue#L359-L373) | diff 增删色系完全来自 Tailwind 默认板，与 `--rh-success/--rh-danger` 无关 |
| `#eab308`（金色星标） | [PromptList.vue#L399](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Prompts/PromptList.vue#L399) | 收藏态又引入第五种主色（橙/青柠/绿/琥珀/金） |
| `rgba(5,150,105,…)` + `var(--rh-success)` | [PromptDetail.vue#L565-L574](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Prompts/PromptDetail.vue#L565-L574) | 硬编码 emerald 底 + 令牌色文字混用，一个组件里两套绿 |
| `#fff` | [VersionHistoryPanel.vue#L255](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/prompts/VersionHistoryPanel.vue#L255) | 应为 `--rh-text-inverse` |

**结果：全站实际使用的强调色系有 5–7 套（橙 / 青柠 / 草绿 / emerald / 琥珀 / 金 / 灰蓝），任何"颜色=含义"的设计意图都已失效。**

### 1.5 （P2）Element Plus 覆盖是靠 `!important` 硬压

[theme.css#L31-L42](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/styles/theme.css#L31-L42) 12 条规则里几乎每一条都带 `!important`，部分带多个（`.el-input__wrapper` 同时压 `box-shadow`+`background`+`border-radius`+`transition`）。这是"覆盖不了才加 !important，加完又覆盖不了再加"的典型结果，后续任何组件级样式都会陷入优先级战争。

### 1.6 （P2）字体策略自相矛盾

1. **`index.html` 预加载了 Inter（含 `<link rel="preload">`），但整个 CSS 里没有任何一处使用 Inter。**（[index.html#L9-L11](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/index.html#L9-L11) vs [global.css#L5](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/styles/global.css#L5)）
   → 关键渲染路径上多了一次跨域字体请求（Google Fonts，部分网络环境下会阻塞/超时），收益为零。
2. **`'Noto Sans SC'` 没有加载**，只写了 font-family。缺字时回退 `PingFang SC`（仅 macOS）→ `Microsoft YaHei`（仅 Windows）→ 系统默认。Linux / 服务器预览 / 移动端渲染中文的字形与字重会与设计稿不一致。
3. **标题用 `Georgia, 'Times New Roman', serif`**（NavBar/Dashboard/Login/viz-card）。Georgia 是 Windows/macOS 预装但 Linux 无（生产服务器与部分用户环境无），会退化到 Times New Roman 或默认衬线 —— 同一页面在不同机器上是两种标题观感。
4. **一个产品两套标题体系**：
   - 衬线：Dashboard `h1`（[48px Georgia 500](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Dashboard.vue#L58)）、Login（[clamp(40,5vw,72) Georgia](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Login.vue#L268)）、图表卡 `h3`（[18px Georgia](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/dashboard/TagCloud.vue#L71)）、NavBar 品牌名
   - 无衬线加粗：Settings/Plaza/PromptList 的 `h1`（[26px 700](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Settings.vue#L207)）、NoteReader/PlazaDetail 内容标题（[30px 700](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteReader.vue#L138)）、PromptDetail（[22px 700](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Prompts/PromptDetail.vue#L416)）
   → 从工作台点进"笔记库"，标题从衬线变无衬线，字号从 48 变 26/30 再变 22，这是**视觉语言断裂**，不是风格统一。

### 1.7 （P1）与既定设计规范冲突

项目规范（`.trae` 用户规则）明确要求：**样式 Tailwind CSS + 黑白极简（#000000 / #FFFFFF / #F5F5F5 / 强调色 #2563EB）**。

实际情况：
- **没有任何 Tailwind 配置**（无 `tailwind.config.*`、`package.json` 无 tailwind 依赖）
- 配色是**暖米底 `#f5f3ee` + 珊瑚橙 `#e85d3f` + 青柠 `#b7d84b`** 的"编辑室工作台"主题
- 唯一的蓝 `#2563EB` 不存在；唯一的 `#f5f5f5` 出现在 [PlazaDetail 的兜底值](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/PlazaDetail.vue#L244)

**要么更新规范，要么承认实现偏离规范。二者必须对齐，否则后续每个页面都会继续各自发挥。**

---

## 二、可访问性（WCAG 2.1 AA）——用实测数据说话

### 2.1 实测对比度表（最严重的部分）

按 WCAG 2.1 相对亮度公式实算：

| 前景 | 背景 | 对比度 | AA 标准 | 判定 | 实际用途 |
|---|---|---|---|---|---|
| `#e85d3f` 主色上白字 `#fff` | `#e85d3f` | **3.46:1** | 4.5:1（<18.66px） | ❌ 不通过 | **所有 `el-button--primary` 按钮文字** |
| `--rh-text-tertiary #8b9087` | `--rh-bg-base #f5f3ee` | **2.94:1** | 4.5:1 | ❌ 严重不通过 | eyebrow、日期、计数、提示文案（10–13px） |
| `--rh-text-tertiary #8b9087` | `--rh-bg-card #fbfaf6` | ≈2.87:1 | 4.5:1 | ❌ 严重不通过 | 卡片内全部辅助文字 |
| `--rh-text-placeholder #b4b8ae` | `--rh-bg-card #fbfaf6` | **1.93:1** | 4.5:1 | ❌ 严重不通过 | 所有输入框 placeholder（"请输入用户名"…） |
| `--rh-success #3f8f6b` | `#fbfaf6` | **3.76:1** | 4.5:1 | ❌ 不通过 | **PromptDetail「生成结果」整段正文文字** |
| `--rh-ai-strong #789415` | `#fbfaf6` | **3.33:1** | 4.5:1 | ❌ 不通过 | NavBar「AI」角标（10px）、`ai-label` |
| `--rh-primary #e85d3f` | `#fbfaf6` | **3.31:1** | 4.5:1 | ❌ 不通过 | 全局链接 `a`、Tab 激活态、`code` 文字、变量高亮 |
| `--rh-text-secondary #5c625b` | `#f5f3ee` | 5.65:1 | 4.5:1 | ✅ | 次要文字（唯一合规档） |
| `--rh-text-primary #20231f` | `#f5f3ee` | ≈14:1 | 4.5:1 | ✅ | 正文 |
| 深色主题 tertiary `#858b82` | `#181a18` | 5.01:1 | 4.5:1 | ✅ | — |

**关键结论：浅色主题的"辅助文字层"整体不可读。** 而"辅助文字"恰恰承载了日期、更新提示、计数、字段说明、快捷键提示等全部元信息。

**特别严重**：
- `#e85d3f` + 白字 3.46:1 —— 这是主色，意味着**全站主按钮不合格**。修一个色值就能全站受益，性价比最高。
- `#b4b8ae` placeholder 1.93:1 —— 用户看表单时几乎看不见输入提示。
- 白色文字 `#fff` 直接写在主色上，而非用 `--rh-text-inverse #fffef9`，两处值不一致。

### 2.2 （P1）深色主题存在"半成品区域"

| 位置 | 问题 |
|---|---|
| [NoteReader](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteReader.vue#L210-L224) / [PlazaDetail](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/PlazaDetail.vue#L309-L323) | 代码块固定近黑底 + 固定近白字，**深色模式下与页面背景 `#181a18` 无区分度** |
| [PromptEditor](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Prompts/PromptEditor.vue#L462-L465) | 深色模式下变量高亮改用 `--rh-primary-hover`，而浅色用 `--rh-warning` —— **同一元素的语义色随主题改变** |
| [VersionHistoryPanel](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/prompts/VersionHistoryPanel.vue#L359-L373) | diff 的 `#ecfdf5/#fef2f2` 浅底在深色面板上是"两块刺眼白斑" |

### 2.3 （P0）焦点可见性被主动移除

```
WysiwygEditor:  :deep(.editor-content) { outline: none }   L217
WysiwygEditor:  :deep(.editor-content:focus) { outline: none }  L224-225
WysiwygEditor:  :deep(.ProseMirror) { outline: none }      L229
PromptEditor:   .var-textarea { outline: none }           L409
```

- 富文本编辑区的 focus 轮廓被 **两处重复** 显式移除，键盘用户看不到"我正在编辑哪里"。
- 除此之外，[NavBar](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/NavBar.vue) / [NoteTree](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteTree.vue) / [Dashboard](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Dashboard.vue) 里的自定义 `<button>`（`.nav-link`、`.quick-create`、`.icon-button`、`.search-launch`、`.resource-row`）**全部没有自定义 focus 样式**，也没有 `:focus-visible` 规则 —— 只能靠浏览器默认轮廓（且部分被 `border:0` 削弱）。
- 全局搜索 `focus-visible`：**0 处命中**。

### 2.4 （P0）键盘与触屏可达性

| 问题 | 位置 | 说明 |
|---|---|---|
| **核心操作只存在于右键菜单** | [NoteTree.vue#L42-L55](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteTree.vue#L42-L55)、[NoteContent.vue#L181-L192](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteContent.vue#L181-L192) | 目录的"新建子目录/重命名/删除"、笔记的"编辑/置顶/删除"**只能右键**。键盘用户、触屏用户、以及不知道能右键的用户（尤其新用户）完全触达不了。且卡片上没有任何"⋯"更多按钮作为替代入口 |
| **`<ul><li>` 当菜单用** | 同上 | 无 `role="menu"` / `role="menuitem"`、无 `tabindex`、无方向键导航、无 Esc 关闭。`<li class="divider">` 是分隔线却用列表项承载 |
| **菜单定位不防溢出** | 同上（`clientX/clientY` 直出） | 在视口右下角右键，菜单会跑到屏幕外，无法完整点击 |
| **卡片/可点区域是 `<div>`** | [Plaza.vue#L41](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Plaza.vue#L41)、[PromptList.vue#L93](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Prompts/PromptList.vue#L93)、[NoteContent.vue#L105-L111](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteContent.vue#L105-L111)、[VersionHistoryPanel.vue#L11](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/prompts/VersionHistoryPanel.vue#L11) | 不可 Tab 聚焦、不可 Enter 触发、不能被屏幕阅读器识别为可点 |
| **导航用 `<button>` 而非 `<a>`** | [NavBar.vue#L14](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/NavBar.vue#L14)、[#L22](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/NavBar.vue#L22)、[#L27](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/NavBar.vue#L27) | 失去中键新标签打开、右键"在新标签页打开"、状态栏链接预览。**导航天然是链接，不是按钮** |
| **品牌区 `<div @click>`** | [NavBar.vue#L3](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/NavBar.vue#L3) | 不可聚焦、无 role、无键盘 |
| **图标按钮无文字标签** | [NoteTree.vue#L5-L7](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteTree.vue#L5-L7)（"+"新建根目录）、[PromptList.vue#L51-L53](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Prompts/PromptList.vue#L51-L53)（"+"新建分类） | 无 `aria-label`、无 tooltip，屏幕阅读器读到空按钮；视觉上也不明确「+」是什么 |
| **`el-form-item` 的 label 不是 `<label>`** | Login/Settings/PromptEditor 全部表单 | Element Plus 的 label 是 `div`，**没有 `for`/`id` 关联**，屏幕阅读器不会朗读字段名；点击 label 也不会聚焦输入框 |
| **完全无 `aria-*`** | 全项目 | 仅 NavBar 两处 `aria-label` 是唯一命中；无 `aria-live`（自动保存、导入进度、错误全部无播报） |

### 2.5 （P2）其他 a11y 缺口

- **Emoji 混入 UI**：[NoteReader.vue#L35](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteReader.vue#L35) `📌 置顶`、[VersionHistoryPanel.vue#L67-L69](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/prompts/VersionHistoryPanel.vue#L67-L69) `🏷 production`。Emoji 在不同系统渲染为不同图形（Windows 彩色、部分 Linux 黑白），且与项目"极简线性图标"的语言冲突，屏幕阅读器会读成 "pushpin" 之类噪音。
- **diff 仅靠颜色区分增删**：虽然 `+`/`-` 标记部分缓解，但 `#ecfdf5` vs `#fef2f2` 在红绿色盲下几乎同色，应叠加纹理/左侧色块。
- **`prefers-contrast` / `forced-colors`** 无适配（只有 `prefers-reduced-motion`，[global.css#L14](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/styles/global.css#L14) 这条做得好）。
- **滚动条仅 Webkit**（[theme.css#L42](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/styles/theme.css#L42)）：Firefox 下是不一致的默认滚动条。

---

## 三、布局与栅格：五套外壳、三种栅格

### 3.1 页面外壳五套并存

| 页面 | padding | max-width | 标题字号 | 标题字体 | 栅格方案 |
|---|---|---|---|---|---|
| Dashboard | `44px 44px 72px` | 1180px | clamp(30–48) | Georgia 衬线 | 自定义 grid |
| NotesPage | 0（贴边） | 无 | — | — | flex 320px 固定侧栏 |
| NoteContent 列表 | `24px 32px` | 900px | 20px 700 | 无衬线 | flex column |
| NoteReader | `24px 32px` | 860px | 30px 700 | 无衬线 | 单列 |
| PromptList | `28px 32px` | 1400px | 26px 700 | 无衬线 | `el-col` 24 栅格 |
| PromptDetail | `28px 32px` | 1200px | 22px 700 | 无衬线 | `el-row` 14/10 |
| PromptEditor | `32px 40px` | 1200px | 20px 700 | 无衬线 | `el-row` 16/8 |
| Plaza | `28px 32px` | 1400px | 26px 700 | 无衬线 | flex + `flex-basis` 三等分 |
| PlazaDetail | `28px 32px` | 960px | 30px 700 | 无衬线 | 单列 |
| Settings | `28px 32px` | 800px | 26px 700 | 无衬线 | 单列 el-card |

**后果**：
- 从「提示词库(1400)」进「提示词详情(1200)」再进「编辑(1200)」，内容左右边界来回跳 200px；
- 从「广场(1400)」进「广场详情(960)」跳 440px；
- 顶部留白 28/32/44 三档并存，页面切换时首屏内容垂直位置抖动。

### 3.2 （P1）三种栅格系统混用

- **自定义 flex + `flex-basis`**：Plaza（[L201](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Plaza.vue#L201)）、NoteContent
- **`el-col` 24 栅格**：PromptList（[L92](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Prompts/PromptList.vue#L92)）—— 且 **`el-col` 外面套了一层自定义 `.prompt-col` div，却没有 `el-row` 父级**，栅格 gutter 与换行行为依赖 Element 内部实现，脆弱
- **`el-row/el-col` 组合**：PromptDetail、PromptEditor
- **CSS Grid**：Dashboard `.viz-grid`

四套并存意味着"三列卡片"在三个页面里三个断点表现不同：Plaza 在 900px 变两列、640px 变一列；PromptList 靠 `xs24/sm12/md8/lg6`；Dashboard 图表固定两列到 800px 才变一列。

### 3.3 （P1）标题字体两套体系混用

见 [1.6](#16-p2字体策略自相矛盾) 第 4 点。**同一产品里"页面标题"既可能是 48px 衬线，也可能是 26px 无衬线** —— 这不是层次，是两套系统。

### 3.4 （P2）重复的卡片皮肤

`.viz-card / .viz-head / .eyebrow / .viz-chart / .viz-empty` 这 5 条规则在 4 个图表组件里**逐字复制了 4 遍**（[TagCloud](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/dashboard/TagCloud.vue#L68-L76)、[CreationTrend](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/dashboard/CreationTrend.vue#L77-L85)、[CategoryDonut](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/dashboard/CategoryDonut.vue#L60-L68)、[UsageHeatmap](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/dashboard/UsageHeatmap.vue#L93-L101)）。图表卡本应是同一个组件（同样的边框/内边距/标题阶），却复制粘贴。此外 `.viz-card` 与 Dashboard `.panel`（[L62](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Dashboard.vue#L62)）又是同一种皮肤的第二套实现。

`.eyebrow` 同样在 Dashboard 与 4 个图表组件里各写一遍。

### 3.5 （P2）圆角无阶梯

实际出现的圆角：`2px / 3px / 4px / 5px / 6px / 8px / 10px / 12px / 50%`。设计令牌只承认 `3 / 5 / 8`。
- 广场卡片 `12px`（[Plaza.vue#L209](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Plaza.vue#L209)）
- 树节点 `6px`（[NoteTree.vue#L415](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteTree.vue#L415)）
- 代码块 `10px`（NoteReader / PlazaDetail）
- diff 行 `2px`（[VersionHistoryPanel.vue#L343](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/prompts/VersionHistoryPanel.vue#L343)）

同名同类元素（"内容块"）在 3 个页面有 3 种圆角。

### 3.6 （P1）响应式断裂点

| 断点 | 问题 |
|---|---|
| **Login 760px** | 栅格 `minmax(0,1.15fr) minmax(360px,.85fr)`。在 **761–900px** 区间，右侧最小 360px + 左侧最小 0，左侧介绍区被压到几近为 0，标题 `clamp(40,5vw,72)` 会溢出/挤压 |
| **NotesPage 640px** | 侧栏改 `height: 280px` 固定高（[L89](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Notes/NotesPage.vue#L89)）。**目录树超过 280px 时内容被裁切**，而外层 `.notes-page` 又是 `overflow-y: auto`，产生嵌套滚动 |
| **NoteContent 空状态文案** | [L11](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteContent.vue#L11) "请从**左侧**选择一个目录" —— 但 ≤640px 时目录跑到了上方。**文案与布局脱节** |
| **VersionHistoryPanel** | 抽屉 `size="700px"` 固定（[L5](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/prompts/VersionHistoryPanel.vue#L5)），<700px 屏幕必然横向溢出 |
| **UsageAnalyticsPanel** | 弹窗 `width="600px"` 固定（[L5](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/prompts/UsageAnalyticsPanel.vue#L5)），且内含 30 行条形图无 `max-height`/滚动区 |
| **NavBar 768px** | 768–900px 之间仍是 224px 固定侧栏，中间断档（iPad 竖屏 768 恰好切到移动版，iPad 横屏 1024 好，但 769–1023 桌面侧栏占掉 224px 后内容局促） |
| **Touch 目标尺寸** | `el-tree` 节点高 34px（[NoteTree.vue#L414](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteTree.vue#L414)）、`fav-icon` 18px 图标（[PromptList.vue#L390](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Prompts/PromptList.vue#L390)）、头像 20px（[Plaza.vue#L54](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Plaza.vue#L54)）—— 均低于 44×44px 触屏最小点击区 |

---

## 四、组件与交互不一致（同名不同样）

### 4.1 （P1）按钮体系没有规则

| 页面 | 顶部动作按钮 | 问题 |
|---|---|---|
| PromptDetail | 返回 / 收藏 / 历史版本 / **发布（warning 或 success 随状态变色）** / 编辑（primary）/ 删除（danger） | **6 个按钮一字排开**；"发布/取消发布"用 `warning↔success` **颜色随状态改变含义**；删除(danger)紧贴编辑(primary)，无误触缓冲 |
| NoteReader | 返回 / 置顶 / **发布（同样 warning↔success）** / 编辑 / 删除 | 同款问题重复一遍 |
| PromptList | [用量分析 + 新建提示词] 用 `el-button-group` 包住 | **分组按钮暗示"同一控件的一组选项"**，但这是两个不相关动作 |
| Settings | 导出用 primary / **success** / **warning** 三色按钮 | 三个**并列、同权重**的导出动作却给了三种颜色 → 颜色不再表示主次，只表示"我随手选了三个颜色" |
| PromptEditor | 头部只有「取消/保存」，无底部固定栏 | 长表单（≥480px 编辑区）滚到底部后**看不到保存按钮** |

**"警告色=取消发布"** 是典型的语义错误：`warning` 应表示"危险/注意"，而"取消发布"只是状态回退。

### 4.2 （P1）标签（el-tag）语义色滥用

| 类型 | 在 Plaza/PlazaDetail 表示 | 在 PromptList 表示 | 在 NoteContent 表示 |
|---|---|---|---|
| `info` | 笔记 | 分类 | **分类** |
| `warning` | **提示词** | **变量名** | 置顶 |
| `success` | — | — | — |

**同一个 `warning` 橙色，在三页分别表示"提示词""变量""置顶"；同一个 `info` 灰色分别表示"笔记"和"分类"。** 颜色语义完全漂移。

此外：
- [PromptEditor.vue#L102-L112](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Prompts/PromptEditor.vue#L102-L112) 用 `warning` 色表示"变量"，而 [VersionHistoryPanel.vue#L462](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/prompts/VersionHistoryPanel.vue#L462) 深色下变量高亮改用 primary —— 同语义两色。
- [PromptEditor.vue#L454-L460](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Prompts/PromptEditor.vue#L454-L460) 变量高亮底 `rgba(217,119,6,.08)` 硬编码 + 文字 `--rh-warning`，与 `el-tag type="warning"` 的官方配色又不一致。

### 4.3 （P1）同类输入两种范式

| 场景 | 实现 | 问题 |
|---|---|---|
| 提示词标签 | `el-select multiple filterable allow-create` + 提示文案（[PromptEditor#L58-L78](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Prompts/PromptEditor.vue#L58-L78)） | 结构化、可发现已有标签 |
| 笔记标签 | **`el-input` + "标签，逗号分隔"**（[NoteContent#L69-L74](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteContent.vue#L69-L74)） | 用户必须自己敲逗号、无已有标签提示、允许输入非法字符 |
| 分类选择 | `el-select clearable`（两处一致） | — |

**"标签"这一个概念，在笔记里是字符串、在提示词里是数组 UI。** 用户在两个模块形成两套肌肉记忆。

### 4.4 （P1）日期格式 4 套、时间语义 4 种

| 位置 | 输出 | 代码 |
|---|---|---|
| Dashboard | `10月20日更新` | [formatTime](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Dashboard.vue#L53) |
| NoteContent 列表 | `10月20日 22:00` | [formatTime](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteContent.vue#L618-L622) |
| NoteReader / PlazaDetail | `2026/10/20 22:00:00` | [toLocaleString('zh-CN')](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteReader.vue#L92) |
| VersionHistoryPanel | `3分钟前 / 2小时前 / 5天前 / 2026/10/20` | [relativeTime](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/prompts/VersionHistoryPanel.vue#L184-L195) |
| Settings | `2026/10/20` | toLocaleDateString |

**同一个应用里，同一个"更新时间"有 5 种呈现。** 且 `toLocaleString('zh-CN')` 输出到秒（`22:00:00`）在阅读页是纯噪音。

### 4.5 （P1）空状态 / 加载态 / 错误态 5 套写法

| 状态 | 实现方式 |
|---|---|
| 加载 | [NoteContent](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteContent.vue#L4-L6) 居中 `Loading` 图标（无文字）；[PlazaDetail](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/PlazaDetail.vue#L4-L6) 居中 `Loading` 图标；[PromptDetail](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Prompts/PromptDetail.vue#L168) `v-loading` 空容器；列表用 `v-loading` 遮罩 |
| 空 | [NoteContent](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteContent.vue#L15-L28) 图标48px+文案+3个按钮；[PromptList](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Prompts/PromptList.vue#L128-L131) 文案+1按钮；[Plaza](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Plaza.vue#L74-L79) 文案+1按钮；[Dashboard](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Dashboard.vue#L16) 图标+文案+**文字链接** |
| 错误 | [PlazaDetail](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/PlazaDetail.vue#L9-L13) 图标48px+文案+按钮；[PromptDetail](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Prompts/PromptDetail.vue#L170-L173) **纯文字+按钮（无图标）**；其余全部靠 ElMessage toast |

**没有一处骨架屏（skeleton）。** 全站加载都是阻塞式转圈/遮罩，首屏（Dashboard 要等 4 个接口）会出现"白屏 → 内容突然跳出"。

### 4.6 （P2）分页条不一致

| 位置 | 样式 |
|---|---|
| PromptList | 居中 + `border-top` + `padding: 20px 0 8px` |
| Plaza | 居中，无上边线，`margin-top: 24px` |
| NoteContent | **`pagination-wrapper` 类在组件内根本没有定义样式**（[L134](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteContent.vue#L134) 引用了类名，scoped 样式中不存在）→ 左对齐、无间距、与列表行贴死 |

### 4.7 （P2）`⌘` 与 `Ctrl` 混用且不识别平台

- Dashboard `⌘ K`（[L8](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Dashboard.vue#L8)）—— Windows 用户看到 Mac 符号
- NoteContent `Ctrl+S 保存`（[L40](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteContent.vue#L40)）—— 实现是 `ctrlKey || metaKey`（正确），但**文案写死 Ctrl**，Mac 用户看到的提示是错的

---

## 五、逐页问题清单

### 5.1 Login（[Login.vue](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Login.vue)）

1. **三重品牌冗余**：左侧 `intro-brand` 有 "R"+ResourceHub；右侧 `login-title` 又是 "ResourceHub"；中间还有一个 `logo-dot` "◆"，但 [L269](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Login.vue#L269) 被 `display: none` 写死（**死代码**）。
2. **登录/注册用 Tabs 而非独立页面**，Tab 切换时整个卡片 `mode="out-in"` 重挂载 —— 用户填到一半切 Tab，输入全部丢失且无提示。
3. **"忘记密码"流程无验证码、无邮箱验证提示**，仅靠"用户名+邮箱+新密码"，且该按钮在登录 Tab 内用 `el-button text size="small"` 与主按钮并排，主次不清（[L48-L50](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Login.vue#L48-L50)）。
4. **[L269](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Login.vue#L269) 用 7 条 `:deep()` + `!important` 强行把 Element 输入框改成 44px 高** —— 一个"输入框高度"要打 3 个选择器、4 处 `!important`（`height/min-height/padding/transform`），脆弱且不可复用。
5. **无 `autocomplete="username" / "current-password" / "new-password"`**，浏览器密码管理器与"记住我"失效。
6. **无"记住我 / 保持登录"**，但后端有 refresh token；用户每次都得重登。
7. 装饰圆环 `::before/::after`（[L266](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Login.vue#L266)）与 Dashboard `overview-panel::after` 同款"切掉一角的圆环"—— 非功能性装饰，且深色大色块 + 圆环正是用户明确表示不喜欢的"压抑深色面板"倾向。
8. **[L273-L276](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Login.vue#L273-L276) 存在第二段非 scoped `<style>`**，仅为给 `.login-intro/.login-panel` 补 `display: flex`，而它们本就在 scoped 里定义了 `display` —— 冗余覆盖。
9. 注册表单未做**实时强度反馈**，只在提交时校验"至少 8 位"。

### 5.2 Dashboard（[Dashboard.vue](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Dashboard.vue)）

1. **"搜索"是假入口**：文案"搜索笔记、提示词、标签..." + `⌘ K`，点击仅 `router.push('/prompts')`（[L8](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Dashboard.vue#L8)）。**首屏最醒目的控件在骗人。**
2. **统计数据是错的**：
   - `stats.favoriteCount` 来自 `promptsStore.prompts`（**仅当前分页**）过滤计数（[L54](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Dashboard.vue#L54)）→ 提示词超过一页时"个收藏"数字偏小
   - `topPrompts` 标称"常用提示词"，但取的是**列表接口返回的前 4 条**，未按 `usage_count` 排序（同 L54）→ **标签与数据不符**
3. "接着上次的地方继续"只取 `recentNotes.slice(0,3)`，但标题承诺"继续"却**不显示上次打开的那一篇**，只显示最近更新的 3 篇。
4. `.resource-row:hover` 改 padding 造成**横向抖动**（[L60](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Dashboard.vue#L60)）。
5. 4 个图表卡固定 `.viz-grid` 两列，`.overview-panel` 深色（[L62](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Dashboard.vue#L62)）—— 与整站浅色基调冲突，形成"页内黑洞"。
6. **标签云随机配色**（[TagCloud.vue#L54](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/dashboard/TagCloud.vue#L54)：`color: () => palette[Math.floor(Math.random()*len)]`）→ **每次渲染、每次切主题颜色都在随机重排**，颜色不携带任何含义。数据可视化里这是明确的反模式。
7. **标签云点击语义不明**：卡片副标题写"点击标签可在笔记中筛选"（[TagCloud#L6](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/dashboard/TagCloud.vue#L6)），点击后 `notesStore.setTag(name)` + 跳 `/notes`。但 `/notes` 页面**没有可见的"当前标签筛选"控件或清除入口**（仅在 [NoteContent#L268](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteContent.vue#L268) 标题里显示"标签：xxx"）→ 用户进入后**不知道如何退出筛选**。
8. 4 个图表卡的口径不一致：标签云统计"笔记+提示词"，分类分布只统计"笔记按一级分类"，热力图只统计"提示词使用"。同一屏 4 张图三种数据范围，**副标题小字才说清（12px/2.87:1 且不可读）**。

### 5.3 NotesPage / NoteTree / NoteContent

1. **NodeTree 中"文件夹"与"笔记"图标尺寸不同**（16px vs 14px，[L380-L398](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteTree.vue#L380-L398)），字号也不同（14px vs 13px）→ 同层级视觉不一致。
2. **"点击分类名"不展开**（`expand-on-click-node="false"`，[L17](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteTree.vue#L17)），只能点**小图标**才展开。与文件树通用心智模型（单击展开）相反，且图标只有 16px，命中区极小。
3. **同时存在两套展开控件**：Element 自带的三角箭头 + 自定义文件夹图标都可展开 → 重复且互相干扰。
4. **树的层级缩进 + 左侧 3px 高亮条 + `highlight-current` 背景 + hover 背景**叠加，选中态信息过载（[L423-L437](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteTree.vue#L423-L437)）。
5. **`.context-menu` 这个类在项目里被定义了两次**：[NoteTree.vue 的 scoped 版](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteTree.vue#L440-L481)（带 `scaleIn` 动画）和 [NoteContent.vue 的全局非 scoped 版](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteContent.vue#L625-L667)（无动画）。全局那份会**泄漏并覆盖/影响全站**，且两处动画行为不一致。
6. **笔记卡片的"置顶"没有直接入口**，只能右键 → 与目录树右键菜单同样的可达性问题。
7. **编辑器标题输入 `size="large"`，标签却是逗号分隔的纯文本框**（见 4.3）。
8. **"退出编辑"无未保存拦截**（[cancelEdit#L474-L482](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteContent.vue#L474-L482)）→ 写了一屏内容点"退出编辑"直接丢。自动保存只在新笔记首次创建后生效（`editingNoteId` 依赖第一次手动保存），**新建笔记后不点保存 = 全部丢失**（[handleSave#L513-L519](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteContent.vue#L513-L519)）。
9. **编辑器无法插入链接/图片/表格/引用语言**（[WysiwygEditor 工具栏](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/WysiwygEditor.vue#L4-L100) 只有粗/斜/删/h1-3/两列表/引用/代码块/分割线），**但阅读态却渲染了表格、图片、链接的样式** → 用户能看的格式，编辑时创建不出来。
10. **工具栏图标语言混杂**：`B`（真字加粗字形）、`I`、`S`（划线 span 内联样式）、`H1/H2/H3`（纯文本）、`List 图标`、`1.`（纯文本）、`ChatLineRound 图标`、`{ }`（内联样式）、`—`（em dash）。**9 个按钮用了 5 种视觉语言**（[L6-L96](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/WysiwygEditor.vue#L6-L96)）。
11. **工具栏激活态用 `type="primary"` 实心橙块**，一排按钮里亮起一个橙色方块，视觉噪音大；且 `<div style="flex: 1">` 内联样式占位（L99）。
12. **未实现撤销/重做按钮**（StarterKit 自带 history）。
13. **[WysiwygEditor.vue#L351-L366](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/WysiwygEditor.vue#L351-L366) 的 `.save-status/.status-saving/.status-saved/.status-error` 是死代码**：模板里从未使用（组件没有任何"保存中/已保存"反馈 UI）。**自动保存对用户完全不可见** —— 用户无从判断内容是否已保存。
14. `:deep(.ProseMirror p.is-editor-empty:first-child::before)` 规则**重复写了两遍**（L233-L239 与 L342-L348）。
15. NoteContent 里 `isCreating` 编辑区与列表区共享 `.editor-meta-form`，但**没有"字数统计""最后保存时间""保存状态"**。

### 5.4 PromptList / PromptDetail / PromptEditor

1. **PromptList 筛选栏"分类"下拉旁挂一个裸「+」图标按钮**（[L51-L53](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Prompts/PromptList.vue#L51-L53)）→ 用户不知道点 + 是"新建分类"（无 tooltip、无 aria-label），且它与"分类"下拉的从属关系靠视觉猜测。
2. **筛选栏 5 个控件权重均等**（搜索/分类/标签/仅收藏/计数），无"清除全部筛选"入口（[L22-L86](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Prompts/PromptList.vue#L22-L86)）。叠加 `showFavoritesOnly`（可由侧栏"收藏提示词"从外部置为 true）后用户更难恢复。
3. **筛选状态未同步到 URL**（无 query 参数）→ 刷新丢失、无法分享、返回上一页状态错乱。
4. `.prompt-card:hover { transform: scale(1.015) }` —— 与 Plaza 的 `translateY(-2px)` 不一致（见 1.3）。
5. **`fav-icon` 18px 图标直接当按钮**（[L96-L103](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Prompts/PromptList.vue#L96-L103)）：无 aria-label、无 tooltip、点击区 < 44px，且**与整卡点击区域重叠**（必须 `@click.stop`），误触率高。
6. **PromptDetail 头部 6 个按钮无分组**（见 4.1），"删除"与"编辑"相邻。
7. **PromptDetail「填充变量」流程过长**：实时预览开关 → 预览框 → 预设下拉 → 另存为 → N 个变量输入 → 生成按钮 → 分隔线 → 结果框 + 复制 + 使用。（[L86-L161](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Prompts/PromptDetail.vue#L86-L161)）**两侧信息重复**：左栏已经展示了完整模板原文，右栏实时预览又是同一内容的不同渲染 → 首屏信息密度过高。
8. **"使用 (N)" 按钮的计数逻辑可疑**：`usage_count + (hasUsed ? 1 : 0)`（[L155](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Prompts/PromptDetail.vue#L155)）→ 显示的是"乐观估计"而非服务端返回值，刷新后又变回去，**数字前后不一致**。
9. **`.rendered-content` 用 `--rh-success` 绿色作为整段正文颜色**（[L565-L574](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Prompts/PromptDetail.vue#L565-L574)）→ 对比度 3.76:1 不合格，且"成功绿"被当作正文色。
10. **勾选框 "标记为收藏" 放在表单最底部**（[PromptEditor#L126-L128](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Prompts/PromptEditor.vue#L126-L128)），但它其实是**列表操作**，与"保存"无关，位置语义混乱。
11. **PromptEditor 头部的"commit 说明"输入框对新建场景无意义**（[L12-L18](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Prompts/PromptEditor.vue#L12-L18)），且默认空 → 版本历史里全是"无描述"（[VersionHistoryPanel#L28](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/prompts/VersionHistoryPanel.vue#L28)）。
12. **变量高亮用"透明 textarea 叠在高亮层上"的 hack**（[L84-L94 / L376-L420](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Prompts/PromptEditor.vue#L376-L420)）：两层字体/字号/行高/内边距/换行策略必须**逐像素一致**（当前都是 `14px/1.7/16px 20px/pre-wrap`），任何一处改动都会导致文字错位。且高亮层的 `hl-brace` 用 `visibility: hidden` 隐藏花括号来"占位对齐"，这是极脆弱的排版技巧。
13. **PromptEditor 无底部固定操作栏**（见 4.1），`min-height: 480px` 的编辑区让页面必然长滚动。

### 5.5 Plaza / PlazaDetail

1. **卡片整块可点 + 内含"复制"按钮**（[Plaza#L41-L68](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Plaza.vue#L41-L68)）：卡片是 `<div @click>`（非焦点可达），按钮用 `@click.stop` 逃逸。**可点区域语义混乱**，且键盘用户完全无法打开详情。
2. **"复制"按钮用 `type="primary" plain`**，与 PromptList 的 primary 实心按钮、PromptDetail 的 primary 实心按钮**不是同一个视觉权重**，但都是"主要动作"。
3. **`item.tags.length` 无空值保护**（[L49](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Plaza.vue#L49)、[PlazaDetail#L52](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/PlazaDetail.vue#L52)）→ `tags` 为 `undefined` 时整卡渲染中断（该字段由 API 决定，属边界）。
4. **作者头像 20px + 头像内文字**（[L54-L56](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Plaza.vue#L54-L56)）→ 20px 圆内塞 12px 首字母，极其局促；PlazaDetail 用 26px，NoteReader 无头像。**头像尺寸无阶梯**。
5. **`{{ total }} 个` / `count-info`** 的"个"用在"内容"上语感生硬（[Plaza#L28](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Plaza.vue#L28)、[PromptList#L83](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Prompts/PromptList.vue#L83)）。
6. **空状态文案"广场还很安静，去发布你的第一篇内容吧"** + 按钮文案由 `plazaStore.contentType` 动态切换（[L76-L78](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Plaza.vue#L76-L78)）→ 但按钮文字用"去笔记库发布"，而**"发布"动作实际在笔记详情页里**，跳过去是列表页，用户还得再点开一篇笔记才能发布。**文案承诺的路径与实际路径不符。**
7. **PlazaDetail 无面包屑**，只有"返回广场"文本按钮（[L19-L21](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/PlazaDetail.vue#L19-L21)）→ 深链进入（从分享链接）后无从得知所处层级。
8. **PlazaDetail 顶部"复制到我的库"与卡片上的"复制"是同名异义**（卡片"复制"= fork 到我的库并弹确认框；文案"复制"易被理解为"复制到剪贴板"），而 PromptDetail 里真正的剪贴板动作也叫"复制"。**同一个词三种含义。**
9. **`pre.detail-plain` 与阅读态的代码块样式完全不同**但都是"等宽文本块"（见 1.4）。
10. **`.detail-content` 标题层级与 NoteReader 硬编码了几乎相同的 20 条规则**（h1/h2/h3/p/ul/ol/li/code/pre/blockquote/img/table/th/td/hr）—— **两处逐条复制**，Markdown 排版样式应抽成共享样式。

### 5.6 Settings

1. **全站最"素"的页面**：`el-card` + `el-descriptions border` + 三个彩色按钮。与 Dashboard/Notes 的编辑室风格（衬线标题、细分割线、eyebrow）**完全脱节**，页面标题 26px 无衬线加粗，与 Dashboard 的 48px 衬线截然不同。
2. **无主题设置项**（但主题是全站唯一的外观开关）→ **设置页缺少最该有的设置**。
3. **"修改密码"无"当前密码是否正确"的即时反馈**，只在 toast 报错。
4. **导出按钮三色**（primary/success/warning，[L55-L63](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Settings.vue#L55-L63)）→ 颜色无语义。
5. **导出无进度/无文件大小预估**，`page_size: 1000` 硬编码（[L143-L145](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Settings.vue#L143-L145)）→ 超过 1000 条**静默截断**，用户以为导全了。
6. **"关于"里的版本号 `v0.1.0 (MVP)` 与 `package.json` 的 `0.1.0` 需手动同步**（无构建注入）。
7. **[L16](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Settings.vue#L16) 用 `toLocaleDateString()`**（默认 locale，非 `zh-CN`）→ 与全站其他日期格式都不同。
8. 无"危险区"分区（删号/清空数据等），但也没有这类功能——不算缺陷，但描述"管理你的账户和数据"言过其实。

### 5.7 NavBar

1. **桌面端无主题切换**（见 P0 #4）。
2. **`<kbd>N</kbd>` 是假快捷键**（[L9](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/NavBar.vue#L9)）。
3. **用户弹层无外部点击关闭 / 无 Esc 关闭 / 无 focus 管理**（[L34-L37](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/NavBar.vue#L34-L37)）→ 只能再点一次头像收起，容易"忘了收"。
4. **头像底色用 `--rh-ai` 青柠绿**（[L93](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/NavBar.vue#L93)）→ **AI 语义色用在"用户名首字母"上**，语义污染；且与主色橙形成第二个"品牌色"。
5. **"收藏提示词 / 全部资源"这两个入口语义重叠**："全部资源"跳 `/notes`（其实是笔记库），"收藏提示词"跳 `/prompts` 并预置筛选。**"全部资源"名不副实**（[L22-L24](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/NavBar.vue#L22-L24)）。
6. **移动端菜单不显示"收藏提示词/全部资源"**（[L48-L51](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/NavBar.vue#L48-L51)）→ 功能在两个端不对称。
7. **导航分组标签「工作区」「收藏与分类」**用 10px 全大写字母 + `.12em` 字距（[L88](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/NavBar.vue#L88)）—— 中文没有"大写"概念，该样式对中文无意义（`text-transform: uppercase` 只对拉丁字符生效），是照搬英文设计的残留。
8. **品牌副标题"个人资源工作台"** 与 Login 的"知识管理与 AI 提示词库"、Dashboard 的"继续整理你的知识。"—— **同一产品三种定位表述**。
9. `--rh-topbar-height: 68px` 与移动端实际 60px 不一致（[global.css#L13](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/styles/global.css#L13) 用 60 硬编码）。

### 5.8 图表组件（4 个）

1. **皮肤重复 4 遍**（见 3.4）。
2. **TagCloud 随机配色**（见 5.2-6）。
3. **UsageHeatmap 的 visualMap 缺少"0 次"的空白态区分**：`min: 0` 到主色的连续渐变，0 与 1 次视觉上难以区分。
4. **所有图表无数据时的空态只用文字**（`.viz-empty`），且 `min-height: 240px` 强制撑高 → **三个空图卡会让 Dashboard 出现 3 块 240px 的大白板**。
5. **图表用 canvas 渲染**（[useChart](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/composables/useChart.ts#L72)）→ 内容不可被屏幕阅读器读取、不可选中、不可 Ctrl+F。无任何易读数据表作为替代（`aria` 缺失）。热力图的"颜色越深次数越多"对色觉障碍用户无替代编码。
6. **图表字号 10–11px + tertiary 色 2.87:1**（[CreationTrend#L44](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/dashboard/CreationTrend.vue#L44)）→ 坐标轴标签实际不可读。
7. **`useChart` 每次 `data-theme` 变化全量 `setOption(option, true)` 重渲染**（[L68](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/composables/useChart.ts#L68)）→ 标签云因此**重新随机配色**（与 5.2-6 叠加放大）。

---

## 六、功能入口与状态反馈

### 6.1 （P0）功能入口缺失

| 缺失 | 说明 |
|---|---|
| **桌面主题切换** | 唯一入口在移动端顶栏（[NavBar#L44](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/NavBar.vue#L44)）。桌面用户无法切换 |
| **设置页无外观设置** | 也没有"跟随系统"选项（虽然 [main.ts#L18](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/main.ts#L18) 首次会读系统偏好，但一旦手动切过就永久固定） |
| **无全局搜索** | 全站没有真正的搜索入口 |
| **无键盘快捷入口** | 除 `Ctrl+S` 外无任何快捷键 |
| **无面包屑** | 所有二级页面（PromptDetail / PlazaDetail / PromptEditor）只有"返回" |
| **无 404 路由** | [router/index.ts](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/router/index.ts) 无 `pathMatch` 兜底 → 乱输路径得到空白页 |
| **无"清除筛选"** | PromptList / Plaza / NoteContent 标签筛选态都无一键复位 |

### 6.2 （P0）虚假快捷键与假入口

| 承诺 | 现实 | 位置 |
|---|---|---|
| `⌘ K` 打开搜索 | 点击后只是 `router.push('/prompts')`，无搜索、无快捷键 | [Dashboard#L8](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Dashboard.vue#L8) |
| `N` 新建提示词 | 全项目无 `keydown` 监听 `N`（仅 [NoteContent Ctrl+S](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteContent.vue#L527-L532)） | [NavBar#L9](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/NavBar.vue#L9) |

**Ctrl+K / ⌘K 是行业高度约定的命令面板快捷键。** 展示它却不实现，比不展示更伤信任。

### 6.3 （P1）破坏性操作与未保存保护

| 场景 | 现状 |
|---|---|
| 笔记编辑中点"退出编辑" | **无任何未保存提示，直接丢弃**（[NoteContent#L474-L482](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteContent.vue#L474-L482)） |
| 新建笔记后未点保存 | 自动保存依赖首次保存后才建立的 `editingNoteId`，**未保存前离开 = 内容全丢**（[#L513-L519](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteContent.vue#L513-L519)） |
| PromptEditor 点"取消" | 直接丢弃全部输入（[#L19](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Prompts/PromptEditor.vue#L19)） |
| PromptEditor 浏览器前进/后退/关闭标签 | 无 `beforeunload` 保护 |
| 删除提示词 | 有 `ElMessageBox` 确认 ✅ |
| 删除目录 | 确认文案含"不可恢复" ✅ 但用 `type: 'warning'` 而删除按钮是 `danger` —— 确认框类型与操作危险度不匹配 |

### 6.4 （P1）操作反馈缺失

| 缺少 | 位置 |
|---|---|
| **自动保存状态不可见**（"保存中/已保存于 xx:xx"） | WysiwygEditor 样式已写好（`.save-status` 等）但模板从未使用 → [L351-L366](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/WysiwygEditor.vue#L351-L366) 死代码 |
| **文件夹导入进度** | 只有 `12px` 灰色文字"正在导入 3/50"（[NoteContent#L25](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteContent.vue#L25)），无进度条，长任务无预期 |
| **复制成功反馈** | 仅 toast，无按钮内联状态变化 |
| **收藏/置顶** | 仅 toast + 图标颜色变化 |
| **无重试入口** | 所有请求失败只有 toast，无"重试"按钮 |
| **无离线/网络异常提示** | — |

---

## 七、信息架构与文案

| 问题 | 位置 | 建议 |
|---|---|---|
| **"全部资源"实际是"笔记库"** | [NavBar#L23](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/NavBar.vue#L23) | 改名"我的笔记"，或真做成聚合页 |
| **"收藏提示词"是筛选而非页面** | [NavBar#L22](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/NavBar.vue#L22) | 归入提示词库的筛选区内，而非一级导航 |
| **"复制"一词三种含义**（卡片复制=克隆到我的库 / 详情复制=同 / PromptDetail 复制=剪贴板） | Plaza / PlazaDetail / PromptDetail | 分别改为"克隆到我的库"/"复制文本" |
| **"使用 N 次" 与 "使用" 按钮语义缠绕** | PromptDetail | — |
| 品牌副标题三种表述 | NavBar / Login / Dashboard | 统一一句 |
| `个` 作量词描述"内容" | Plaza / PromptList | 改"条/篇"或去掉量词 |
| 空态"请从左侧选择"在移动端错误 | NoteContent | 改为"请先选择一个目录" |
| 导入文件夹前未说明"仅支持 .md/.markdown" | [NoteContent#L94](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/components/notes/NoteContent.vue#L94) | 选择器已限制但用户不知道 |
| 变量说明"点击插入到光标位置"作 label | [PromptEditor#L97](file:///d:/大学就业指导/项目相关/项目落地（全栈）/ResourceHub/frontend/src/views/Prompts/PromptEditor.vue#L97) | 把操作说明当字段标签，label 应只写"变量" |
| eyebrow 全大写字母 + `.12em` 字距用于中文 | Dashboard / NavBar / 4 图表 | 中文无大写，该规则无效 |

---

## 八、修复优先级建议

### P0 — 立刻修（低成本、高收益）

1. **补齐 6 个幽灵令牌**：在 `theme.css` 定义 `--rh-bg-subtle`、`--rh-border-light`、`--rh-primary-lighter`、`--rh-bg-secondary`、`--rh-transition`（或把引用改成已有令牌）。**一处修复，全站状态恢复可见性。**
2. **主色对比度**：`#e85d3f` 调深至能承载白字 4.5:1（约 `#c2492c` 以下），或主按钮文字改用深色。同步修正 `--rh-text-tertiary` 至少到 4.5:1（约 `#6e736b`）。
3. **补 focus 样式**：删除 WysiwygEditor / PromptEditor 的 `outline: none`，加全局 `:focus-visible` 环形轮廓。
4. **给右键菜单补替代入口**：列表行/卡片右侧加"⋯"按钮，键盘可达。
5. **桌面端加主题切换**（NavBar 底部 + Settings 增加"外观"分区）。
6. **删除 `⌘ K` 与 `N`**，或真正实现快捷键。
7. **把"搜索"按钮改为真搜索**（至少聚焦输入框），或改文案为"前往提示词库"。
8. **统一 `isCreating` 路径下的首次保存**，加"未保存离开"拦截。

### P1 — 本迭代内做

9. 统一页面外壳：抽出 `<PageShell>`（统一 padding / max-width 分档 / 标题阶），或对齐到 2 档（内容型 880–960px、列表型 1200–1400px）。
10. 统一标题字体：二选一。建议**全部统一为无衬线**（中文衬线在小字号下观感差），或全部衬线并加载对应 Web 字体。
11. 建立**字号阶梯令牌**（12/14/16/20/26/34）并把 17 个散值收敛。
12. 移除 `transition: all`，改为具体属性。
13. 为 `--rh-*` 常量新增 `--rh-success-strong` 等，替换全部 `#10b981/#ef4444/#ecfdf5/#fef2f2/#eab308/#1c1917`。
14. 修代码块在深色模式下的可见性（改用 `--rh-bg-inset` + `--rh-text-primary`）。
15. 统一日期格式（建议 1 套：`10月20日` / 详情页 `2026-10-20 22:00`）。
16. 统一标签输入（笔记也用 tag select）。
17. 统一空/加载/错误态为 3 个共享组件 + 引入 skeleton。
18. 卡片悬停统一为一种（建议 `translateY(-2px) + border-color`），移除 padding 变化。
19. 图表：固定配色表（按顺序取色，不随机）、加大轴标签字号与对比度、为图表补可读数据表。
20. 弹层宽度改响应式（`min(700px, 100vw - 32px)`）。
21. NoteTree：单击分类名展开；去掉重复的展开控件；图标与字号对齐。
22. 移除 NoteContent 里那份**全局** `.context-menu`（消除全站泄漏）。
23. 补 `autocomplete`、`<label for>`、图标按钮 `aria-label`、`aria-live` 播报。
24. 补 `pathMatch: '/:pathMatch(.*)*'` 404 路由。
25. 补 `beforeunload` / 路由守卫级别的未保存拦截。

### P2 — 后续治理

26. 抽出 `VizCard`、`MarkdownTypography`（NoteReader 与 PlazaDetail 的 20 条 Markdown 规则合并）、`EmptyState`、`PageShell`、`ActionGroup`。
27. 消除 `!important`，改用 CSS 变量注入 + 语义类覆盖 Element Plus。
28. 清理死代码：`logo-dot`、`.save-status` 系列、重复的 placeholder 规则、`--rh-transition-all-slow`。
29. 统一圆角为 3 档，清理 10px/12px/6px。
30. 统一 z-index 令牌。
31. 补 Firefox 滚动条、`prefers-contrast`。
32. 抽 `<AppKbd>` 组件处理平台差异（⌘/Ctrl）。
33. 与规范对齐：决定是"改规范"还是"改实现"，并写进 `AGENTS.md`。
34. PromptDetail 折叠"实时预览"到默认关闭，降低首屏密度。

---

## 附录 A：幽灵令牌清单（可直接用于修复）

```css
/* 需在 theme.css :root 与 [data-theme="dark"] 中补齐 */
--rh-bg-subtle:      #ebe9e1;   /* dark: #141614 */
--rh-bg-secondary:   #f1efe9;   /* dark: #202420 */
--rh-border-light:   #e9e7df;   /* dark: #2c312c */
--rh-primary-lighter: rgba(232, 93, 63, 0.14);  /* dark: rgba(255,118,92,.16) */
--rh-transition:     all 200ms cubic-bezier(0.2, 0, 0, 1); /* 建议改为具体属性 */
```

## 附录 B：硬编码色值清单（应替换为令牌）

| 硬编码 | 出现处 | 应替换为 |
|---|---|---|
| `#1c1917` | NoteReader L211、PlazaDetail L310 | `--rh-bg-inset`（或新增 `--rh-code-bg`） |
| `#e7e5e4` | NoteReader L221、PlazaDetail L320 | `--rh-text-primary`（深色代码块专用令牌） |
| `#10b981` | VersionHistoryPanel L260/L364、WysiwygEditor L361 | `--rh-success` |
| `#ef4444` | VersionHistoryPanel L372 | `--rh-danger` |
| `#ecfdf5` / `#fef2f2` | VersionHistoryPanel L360/L368 | `--rh-success-subtle` / `--rh-danger-subtle`（需新增） |
| `#eab308` | PromptList L399/L404 | 新增 `--rh-favorite` |
| `rgba(5,150,105,.04/.15)` | PromptDetail L565/L573 | 同上 |
| `#fff` | VersionHistoryPanel L255 | `--rh-text-inverse` |
| `rgba(217,119,6,.08)` | PromptEditor L455 | `--rh-warning-subtle` |
| `#f5f5f5` | PlazaDetail L244 | `--rh-bg-base` |

## 附录 C：审查方法与局限

- 审查基于**静态源码**：`frontend/src` 全部 `.vue` / `.css` / `.ts`，以及 `index.html`、`package.json`、`vite.config.ts` 的存在性。
- 对比度为按 WCAG 2.1 相对亮度公式**手算**（未使用工具实测渲染结果），误差在 ±0.05 内，不影响判定结论。
- **未做实际浏览器渲染验证**：布局抖动、溢出、断点断裂点等属静态推断，建议在 1440 / 1024 / 768 / 375 四档宽度与浅/深两主题下逐个复核。
- 未审查后端返回字段的完整性对 UI 的影响（如 `tags` 是否可能为 `null`）。

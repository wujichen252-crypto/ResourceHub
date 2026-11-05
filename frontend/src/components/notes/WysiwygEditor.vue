<template>
  <div class="wysiwyg-editor">
    <!-- Toolbar -->
    <div class="editor-toolbar" v-if="editor" role="toolbar" aria-label="笔记编辑工具栏">
      <div class="toolbar-group">
        <el-tooltip content="加粗 (⌘B)" placement="bottom">
          <el-button size="small" aria-label="加粗" :class="{ 'is-active': editor.isActive('bold') }" @click="editor.chain().focus().toggleBold().run()"><span class="tb-glyph tb-bold">B</span></el-button>
        </el-tooltip>
        <el-tooltip content="斜体 (⌘I)" placement="bottom">
          <el-button size="small" aria-label="斜体" :class="{ 'is-active': editor.isActive('italic') }" @click="editor.chain().focus().toggleItalic().run()"><span class="tb-glyph tb-italic">I</span></el-button>
        </el-tooltip>
        <el-tooltip content="删除线" placement="bottom">
          <el-button size="small" aria-label="删除线" :class="{ 'is-active': editor.isActive('strike') }" @click="editor.chain().focus().toggleStrike().run()"><span class="tb-glyph tb-strike">S</span></el-button>
        </el-tooltip>
      </div>

      <el-divider direction="vertical" />

      <div class="toolbar-group">
        <el-tooltip content="标题 1" placement="bottom">
          <el-button size="small" aria-label="标题 1" :class="{ 'is-active': editor.isActive('heading', { level: 1 }) }" @click="editor.chain().focus().toggleHeading({ level: 1 }).run()"><span class="tb-glyph">H1</span></el-button>
        </el-tooltip>
        <el-tooltip content="标题 2" placement="bottom">
          <el-button size="small" aria-label="标题 2" :class="{ 'is-active': editor.isActive('heading', { level: 2 }) }" @click="editor.chain().focus().toggleHeading({ level: 2 }).run()"><span class="tb-glyph">H2</span></el-button>
        </el-tooltip>
        <el-tooltip content="标题 3" placement="bottom">
          <el-button size="small" aria-label="标题 3" :class="{ 'is-active': editor.isActive('heading', { level: 3 }) }" @click="editor.chain().focus().toggleHeading({ level: 3 }).run()"><span class="tb-glyph">H3</span></el-button>
        </el-tooltip>
      </div>

      <el-divider direction="vertical" />

      <div class="toolbar-group">
        <el-tooltip content="无序列表" placement="bottom">
          <el-button size="small" aria-label="无序列表" :class="{ 'is-active': editor.isActive('bulletList') }" @click="editor.chain().focus().toggleBulletList().run()"><el-icon><List /></el-icon></el-button>
        </el-tooltip>
        <el-tooltip content="有序列表" placement="bottom">
          <el-button size="small" aria-label="有序列表" :class="{ 'is-active': editor.isActive('orderedList') }" @click="editor.chain().focus().toggleOrderedList().run()"><span class="tb-glyph">1.</span></el-button>
        </el-tooltip>
        <el-tooltip content="任务列表" placement="bottom">
          <el-button size="small" aria-label="任务列表" :class="{ 'is-active': editor.isActive('taskList') }" @click="editor.chain().focus().toggleTaskList().run()"><span class="tb-glyph tb-task">☐</span></el-button>
        </el-tooltip>
      </div>

      <el-divider direction="vertical" />

      <div class="toolbar-group">
        <el-tooltip content="引用" placement="bottom">
          <el-button size="small" aria-label="引用" :class="{ 'is-active': editor.isActive('blockquote') }" @click="editor.chain().focus().toggleBlockquote().run()"><el-icon><ChatLineRound /></el-icon></el-button>
        </el-tooltip>
        <el-tooltip content="代码块" placement="bottom">
          <el-button size="small" aria-label="代码块" :class="{ 'is-active': editor.isActive('codeBlock') }" @click="editor.chain().focus().toggleCodeBlock().run()"><span class="tb-glyph tb-mono">{ }</span></el-button>
        </el-tooltip>
        <el-tooltip content="分割线" placement="bottom">
          <el-button size="small" aria-label="分割线" @click="editor.chain().focus().setHorizontalRule().run()"><span class="tb-glyph">—</span></el-button>
        </el-tooltip>
        <el-tooltip content="表格" placement="bottom">
          <el-button size="small" aria-label="表格" :class="{ 'is-active': editor.isActive('table') }" @click="toggleTable()"><span class="tb-glyph">⊞</span></el-button>
        </el-tooltip>
      </div>

      <div class="toolbar-spacer" />
      <span class="editor-count" :aria-label="`字数 ${wordCount}`">{{ wordCount }} 字</span>
    </div>

    <!-- Editor Body（含悬浮拖拽手柄） -->
    <div class="editor-body" ref="bodyRef">
      <div
        v-if="dragHandle.visible"
        class="block-drag-handle"
        :style="{ top: dragHandle.top + 'px', left: dragHandle.left + 'px' }"
        aria-label="拖拽块"
        draggable="true"
        @dragstart.prevent="onDragStart"
        @dragover.prevent="onDragOver"
        @drop.prevent="onDrop"
      >⋮⋮</div>

      <editor-content :editor="editor" class="editor-content" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import { TaskList } from '@tiptap/extension-task-list'
import { TaskItem } from '@tiptap/extension-task-item'
import { TableKit } from '@tiptap/extension-table'
import { Image } from '@tiptap/extension-image'
import { CharacterCount } from '@tiptap/extension-character-count'
import { List, ChatLineRound } from '@element-plus/icons-vue'

import { BlockId } from './extensions/BlockId'
import { SlashCommand } from './extensions/slashCommand'
import {
  findTopBlockFromDom, moveTopBlock, posToDomRect,
} from './extensions/topBlockUtils'

const props = defineProps<{
  /** HTML 快照（v-model，脏检查 / 渲染兜底用） */
  modelValue: string
  /** TipTap JSON（权威）；旧 markdown 笔记不传 */
  contentJson?: unknown | null
  noteId?: number
}>()

const emit = defineEmits<{
  'update:modelValue': [html: string]
  'update:contentJson': [json: unknown]
  save: [payload: { id?: number; content: string; content_json: unknown | null }, showToast?: boolean]
  'selection-change': [
    state: { hasSelection: boolean; selectionText: string; rect: { top: number; left: number; bottom: number } },
  ]
}>()

let isSaving = false
const bodyRef = ref<HTMLElement | null>(null)

// ── 悬浮拖拽手柄状态 ──
const dragHandle = reactive<{
  visible: boolean
  top: number
  left: number
  fromPos: number | null
}>({ visible: false, top: 0, left: 0, fromPos: null })

// ── 编辑器实例 ──
const editor = useEditor({
  content: (props.contentJson ?? props.modelValue) as any,
  extensions: [
    StarterKit.configure({
      heading: { levels: [1, 2, 3] },
      codeBlock: {
        HTMLAttributes: {
          class: 'language-text',
        },
      },
    }),
    Placeholder.configure({ placeholder: '开始书写...输入 / 唤出块菜单' }),
    Image as any,
    // TableKit 一次性注册 Table/TableRow/TableHeader/TableCell，缺子节点会导致 Schema 校验失败、正文空白
    TableKit as any,
    TaskList as any,
    TaskItem.configure({ nested: true }),
    CharacterCount as any,
    BlockId,
    SlashCommand,
  ],
  onUpdate: ({ editor: e }) => {
    if (isSaving) return
    const html = e.getHTML()
    const json = e.getJSON()
    emit('update:modelValue', html)
    emit('update:contentJson', json)
  },
  // 选区变化时通知外层（内联 AI 菜单据此弹出/收起）
  onSelectionUpdate: ({ editor: ed }) => {
    const { from, to, empty } = ed.state.selection
    const text = empty ? '' : ed.state.doc.textBetween(from, to, '\n')
    const hasSelection = text.trim().length > 0
    // 用编辑器自身坐标（相对视口），比 window.getSelection 更可靠
    let rect = { top: 0, left: 0, bottom: 0 }
    if (hasSelection) {
      const start = ed.view.coordsAtPos(from)
      const end = ed.view.coordsAtPos(to)
      rect = {
        top: Math.min(start.top, end.top),
        left: start.left,
        bottom: Math.max(start.bottom, end.bottom),
      }
    }
    emit('selection-change', { hasSelection, selectionText: text, rect })
  },
})

// ── 字数显示 ──
const wordCount = computed(() => {
  if (!editor.value) return 0
  const storage = editor.value.storage.characterCount
  if (!storage) return 0
  // characters() 带空格更直观，中文场景更接近真实字数
  return storage.characters?.() ?? storage.words?.() ?? 0
})

// ── 工具栏动作 ──
function toggleTable() {
  const e = editor.value
  if (!e) return
  if (e.isActive('table')) {
    e.chain().focus().deleteTable().run()
  } else {
    e.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()
  }
}

// ── 受控输入同步（props → 编辑器）──
watch(
  () => props.contentJson,
  (newJson) => {
    if (!editor.value) return
    // contentJson 权威；旧 markdown 笔记首次打开后 contentJson 仍为 null，不触发重置
    if (newJson != null) {
      const cur = editor.value.getJSON()
      if (JSON.stringify(cur) !== JSON.stringify(newJson)) {
        editor.value.commands.setContent(newJson as any, { emitUpdate: false })
      }
    }
  },
  { deep: true },
)

watch(
  () => props.modelValue,
  (newHtml) => {
    if (!editor.value || props.contentJson != null) return // JSON 轨优先
    if (newHtml !== editor.value.getHTML()) {
      editor.value.commands.setContent(newHtml || '', { emitUpdate: false })
    }
  },
)

onBeforeUnmount(() => {
  editor.value?.destroy()
  dragHandle.visible = false
  if (bodyRef.value) {
    bodyRef.value.removeEventListener('mousemove', onBodyMouseMove)
    bodyRef.value.removeEventListener('mouseleave', onBodyMouseLeave)
  }
})

onMounted(() => {
  if (bodyRef.value) {
    bodyRef.value.addEventListener('mousemove', onBodyMouseMove)
    bodyRef.value.addEventListener('mouseleave', onBodyMouseLeave)
  }
})

// ── 悬浮手柄：跟随鼠标到当前顶层块左边 ──
function onBodyMouseMove(e: MouseEvent) {
  const e0 = editor.value
  if (!e0) return

  // 悬浮在拖拽手柄自身上时，不要触发新的顶层块检测
  const target = e.target as HTMLElement
  if (target.closest('.block-drag-handle')) return

  // 先看鼠标是否在顶层块区域附近（左边 28px 范围内也显示）
  const hit = findTopBlockFromDom(e0, target)
  if (!hit) {
    dragHandle.visible = false
    return
  }
  const rect = posToDomRect(e0, hit.pos)
  if (!rect) return

  // 手柄贴在顶层块左边 6px、垂直居中对齐到行顶部
  const bodyRect = bodyRef.value!.getBoundingClientRect()
  dragHandle.top = rect.top - bodyRect.top
  dragHandle.left = rect.left - bodyRect.left - 28
  dragHandle.visible = true
  dragHandle.fromPos = hit.pos
}

function onBodyMouseLeave() {
  dragHandle.visible = false
}

// ── 拖拽：HTML5 draggable API + ProseMirror transaction ──
function onDragStart(e: DragEvent) {
  const e0 = editor.value
  if (!e0 || dragHandle.fromPos == null) return
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', String(dragHandle.fromPos))
  }
  // 聚焦编辑器（拖完后保持焦点）
  e0.commands.focus()
}

function onDragOver(e: DragEvent) {
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'move'
}

function onDrop(e: DragEvent) {
  const e0 = editor.value
  if (!e0 || dragHandle.fromPos == null) return
  const from = dragHandle.fromPos
  const coords = { top: e.clientY, bottom: e.clientY, left: e.clientX, right: e.clientX }
  const targetPos = e0.view.posAtCoords(coords as any)
  if (targetPos == null) return

  moveTopBlock(e0, from, targetPos.pos)
  // 触发 onUpdate → 脏检查 → 自动保存链路
  emit('update:modelValue', e0.getHTML())
}

// ── 保存（与 NoteContent.vue handleSave 对接）──
async function triggerSave(showToast?: boolean) {
  if (isSaving) return
  const e0 = editor.value
  if (!e0) return
  isSaving = true
  try {
    emit('save', {
      id: props.noteId,
      content: e0.getHTML(),
      content_json: e0.getJSON(),
    }, showToast)
  } catch {
    // 静默失败
  } finally {
    isSaving = false
  }
}

function manualSave() {
  triggerSave(true)
}

/** 选区纯文本 + 前后各 600 字符上下文（供内联 AI 请求） */
function getInlineContext(): { text: string; context_before: string; context_after: string } {
  const ed = editor.value
  if (!ed) return { text: '', context_before: '', context_after: '' }
  const { from, to } = ed.state.selection
  const docSize = ed.state.doc.content.size
  return {
    text: ed.state.doc.textBetween(from, to, '\n'),
    context_before: ed.state.doc.textBetween(Math.max(0, from - 600), from, '\n'),
    context_after: ed.state.doc.textBetween(to, Math.min(docSize, to + 600), '\n'),
  }
}

/** 在选区末尾之后插入内容（解释 / 提问结果）；选区为空时追加到文末 */
function insertBelow(html: string) {
  const ed = editor.value
  if (!ed) return
  const { selection } = ed.state
  const pos = selection.empty ? ed.state.doc.content.size : selection.to
  ed.chain().focus().insertContentAt(pos, html).run()
}

/** 用新内容替换当前选区（改写结果）；选区为空时退化为追加到文末 */
function replaceSelection(html: string) {
  const ed = editor.value
  if (!ed) return
  const { selection } = ed.state
  if (selection.empty) {
    ed.chain().focus().insertContentAt(ed.state.doc.content.size, html).run()
    return
  }
  ed.chain().focus().insertContentAt(selection, html).run()
}

defineExpose({ manualSave, getInlineContext, insertBelow, replaceSelection })
</script>

<style scoped>
.wysiwyg-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.editor-toolbar {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 16px;
  border-bottom: 1px solid var(--rh-border-light);
  background: var(--rh-bg-card);
  border-radius: var(--rh-radius-md) var(--rh-radius-md) 0 0;
  flex-wrap: wrap;
  position: sticky;
  top: 0;
  z-index: 10;
}

.toolbar-group {
  display: flex;
  gap: 2px;
}

.toolbar-group .el-button {
  min-width: 32px;
  padding: 4px 8px;
}

.toolbar-group .el-button.is-active {
  background: var(--rh-primary-subtle);
  border-color: var(--rh-primary-muted);
  color: var(--rh-primary);
}

.tb-glyph {
  font-family: var(--rh-font-sans);
  font-size: 13px;
  font-weight: 600;
  line-height: 1;
}

.tb-bold { font-weight: 800; }
.tb-italic { font-family: var(--rh-font-display); font-style: italic; }
.tb-strike { text-decoration: line-through; }
.tb-mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
.tb-task { font-size: 14px; color: var(--rh-text-secondary); }

.toolbar-spacer {
  flex: 1;
}

.editor-count {
  font-size: 12px;
  color: var(--rh-text-tertiary);
  padding: 0 4px;
}

.editor-body {
  flex: 1;
  overflow-y: auto;
  padding: 22px 30px;
  border: 1px solid transparent;
  border-radius: 0 0 var(--rh-radius-md) var(--rh-radius-md);
  transition: var(--rh-transition-all-normal);
  position: relative;
}

.editor-body:focus-within {
  border-color: var(--rh-primary);
  box-shadow: var(--rh-focus-ring);
}

/* 悬浮拖拽手柄 */
.block-drag-handle {
  position: absolute;
  width: 18px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  line-height: 1;
  color: var(--rh-text-tertiary);
  cursor: grab;
  border-radius: var(--rh-radius-xs);
  background: var(--rh-bg-subtle);
  border: 1px solid var(--rh-border-faint);
  user-select: none;
  opacity: 0;
  transition: opacity var(--rh-duration-fast) var(--rh-transition-fast),
              color var(--rh-duration-fast) var(--rh-transition-fast);
  z-index: 5;
}

.block-drag-handle:hover {
  opacity: 1;
  color: var(--rh-primary);
}

.editor-body:hover .block-drag-handle {
  opacity: 1;
}

:deep(.editor-content) {
  min-height: 400px;
  font-size: 15.5px;
  line-height: 1.85;
  color: var(--rh-text-primary);
}

:deep(.ProseMirror) {
  min-height: 400px;
}

:deep(.ProseMirror p.is-editor-empty:first-child::before) {
  content: attr(data-placeholder);
  float: left;
  color: var(--rh-text-placeholder);
  pointer-events: none;
  height: 0;
}

/* 顶层块悬停时可看到 data-block-id（开发期辅助），生产可注释掉 */
:deep([data-block-id]::after) {
  /* 预留：以后可做角标显示块 id */
  content: '';
}

:deep(.ProseMirror h1) {
  font-size: 24px;
  font-weight: 700;
  margin: 28px 0 12px;
  border-bottom: 1px solid var(--rh-border-light);
  padding-bottom: 8px;
}

:deep(.ProseMirror h2) {
  font-size: 20px;
  font-weight: 600;
  margin: 24px 0 10px;
  border-bottom: 1px solid var(--rh-border-light);
  padding-bottom: 6px;
}

:deep(.ProseMirror h3) {
  font-size: 17px;
  font-weight: 600;
  margin: 20px 0 8px;
}

:deep(.ProseMirror p) {
  margin-bottom: 12px;
}

:deep(.ProseMirror ul),
:deep(.ProseMirror ol) {
  padding-left: 24px;
  margin-bottom: 12px;
}

:deep(.ProseMirror li) {
  margin-bottom: 4px;
}

:deep(.ProseMirror ul[data-type="taskList"]) {
  list-style: none;
  padding-left: 0;
}

:deep(.ProseMirror ul[data-type="taskList"] li) {
  display: flex;
  gap: 6px;
  align-items: flex-start;
  margin-bottom: 4px;
}

:deep(.ProseMirror ul[data-type="taskList"] li > label) {
  flex-shrink: 0;
  margin-top: 2px;
  cursor: pointer;
}

:deep(.ProseMirror ul[data-type="taskList"] li[data-checked="true"]) > div {
  text-decoration: line-through;
  color: var(--rh-text-tertiary);
}

:deep(.ProseMirror pre) {
  background: var(--rh-bg-inset);
  color: var(--rh-text-secondary);
  padding: 16px 20px;
  border-radius: var(--rh-radius-sm);
  overflow-x: auto;
  margin: 16px 0;
  font-size: 14px;
  line-height: 1.6;
}

:deep(.ProseMirror code) {
  background: var(--rh-bg-subtle);
  color: var(--rh-primary);
  padding: 2px 6px;
  border-radius: var(--rh-radius-xs);
  font-size: 14px;
}

:deep(.ProseMirror pre code) {
  background: none;
  color: inherit;
  padding: 0;
}

:deep(.ProseMirror blockquote) {
  border-left: 3px solid var(--rh-primary);
  padding: 4px 0 4px 20px;
  margin: 16px 0;
  color: var(--rh-text-secondary);
  background: var(--rh-bg-subtle);
  border-radius: 0 var(--rh-radius-sm) var(--rh-radius-sm) 0;
}

/* 内联 AI 产出块：柠檬绿左边线，与普通引用区分 */
:deep(.ProseMirror blockquote.rh-ai-inline) {
  border-left-color: var(--rh-ai-strong);
}

:deep(.ProseMirror hr) {
  border: none;
  border-top: 1px solid var(--rh-border-faint);
  margin: 24px 0;
}

:deep(.ProseMirror img) {
  max-width: 100%;
  border-radius: var(--rh-radius-md);
  margin: 16px 0;
}

:deep(.ProseMirror table) {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
  overflow: hidden;
  border-radius: var(--rh-radius-sm);
}

:deep(.ProseMirror th),
:deep(.ProseMirror td) {
  border: 1px solid var(--rh-border);
  padding: 8px 12px;
  text-align: left;
  font-size: 14px;
}

:deep(.ProseMirror th) {
  background: var(--rh-bg-subtle);
  font-weight: 600;
}

/* 表格边框调整时的 resize handle（TipTap Table 内建） */
:deep(.column-resize-handle) {
  position: absolute;
  right: -2px;
  top: -1px;
  bottom: -2px;
  width: 4px;
  background-color: var(--rh-primary);
  pointer-events: none;
}
</style>

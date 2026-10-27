<template>
  <div class="wysiwyg-editor">
    <!-- Toolbar -->
    <div class="editor-toolbar" v-if="editor" role="toolbar" aria-label="笔记编辑工具栏">
      <div class="toolbar-group">
        <el-tooltip content="加粗" placement="bottom">
          <el-button size="small" aria-label="加粗" :class="{ 'is-active': editor.isActive('bold') }" @click="editor.chain().focus().toggleBold().run()"><span class="tb-glyph tb-bold">B</span></el-button>
        </el-tooltip>
        <el-tooltip content="斜体" placement="bottom">
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
      </div>

      <div class="toolbar-spacer" />
    </div>

    <!-- Editor Content -->
    <div class="editor-body">
      <editor-content :editor="editor" class="editor-content" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { watch, onUnmounted } from 'vue'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import { List, ChatLineRound } from '@element-plus/icons-vue'

const props = defineProps<{
  modelValue: string
  noteId?: number
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  save: [id: number | undefined, content: string, showToast?: boolean]
}>()

let isSaving = false

const editor = useEditor({
  content: props.modelValue || '',
  extensions: [
    StarterKit.configure({
      heading: { levels: [1, 2, 3] },
    }),
    Placeholder.configure({
      placeholder: '开始书写...',
    }),
  ],
  onUpdate: () => {
    if (!editor.value || isSaving) return
    const html = editor.value.getHTML()
    emit('update:modelValue', html)

  },
})

watch(() => props.modelValue, (newVal) => {
  if (editor.value && newVal !== editor.value.getHTML()) {
    editor.value.commands.setContent(newVal || '', { emitUpdate: false })
  }
})

onUnmounted(() => {
  editor.value?.destroy()
})

async function triggerSave(html: string, showToast?: boolean) {
  if (isSaving) return
  isSaving = true
  try {
    emit('save', props.noteId, html, showToast)
  } catch {
    // 静默失败，不打断用户
  } finally {
    isSaving = false
  }
}

function manualSave() {
  if (!editor.value) return
  const html = editor.value.getHTML()
  // 手动保存：即使内容没变也触发（自动保存已同步过，但用户需要确认感）
  triggerSave(html, true)
}

defineExpose({ manualSave })
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

/* 激活态用淡色底 + 主色文字，替代原先的实心色块，降低工具栏视觉噪音 */
.toolbar-group .el-button.is-active {
  background: var(--rh-primary-subtle);
  border-color: var(--rh-primary-muted);
  color: var(--rh-primary);
}

/* 工具栏内的文本字形统一为同一套字体 / 字号 / 字重 */
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

.toolbar-spacer {
  flex: 1;
}

.editor-body {
  flex: 1;
  overflow-y: auto;
  padding: 22px 30px;
  border: 1px solid transparent;
  border-radius: 0 0 var(--rh-radius-md) var(--rh-radius-md);
  transition: var(--rh-transition-all-normal);
}

/* 键盘用户可感知编辑区焦点（原先三处 outline: none 会完全隐藏焦点位置） */
.editor-body:focus-within {
  border-color: var(--rh-primary);
  box-shadow: var(--rh-focus-ring);
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
</style>

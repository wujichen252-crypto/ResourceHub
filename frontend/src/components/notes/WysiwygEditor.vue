<template>
  <div class="wysiwyg-editor">
    <!-- Toolbar -->
    <div class="editor-toolbar" v-if="editor">
      <div class="toolbar-group">
        <el-tooltip content="加粗" placement="bottom">
          <el-button
            :type="editor.isActive('bold') ? 'primary' : 'default'"
            size="small"
            @click="editor.chain().focus().toggleBold().run()"
          ><strong>B</strong></el-button>
        </el-tooltip>
        <el-tooltip content="斜体" placement="bottom">
          <el-button
            :type="editor.isActive('italic') ? 'primary' : 'default'"
            size="small"
            @click="editor.chain().focus().toggleItalic().run()"
          ><em>I</em></el-button>
        </el-tooltip>
        <el-tooltip content="删除线" placement="bottom">
          <el-button
            :type="editor.isActive('strike') ? 'primary' : 'default'"
            size="small"
            @click="editor.chain().focus().toggleStrike().run()"
          ><span style="text-decoration: line-through">S</span></el-button>
        </el-tooltip>
      </div>

      <el-divider direction="vertical" />

      <div class="toolbar-group">
        <el-tooltip content="标题 1" placement="bottom">
          <el-button
            :type="editor.isActive('heading', { level: 1 }) ? 'primary' : 'default'"
            size="small"
            @click="editor.chain().focus().toggleHeading({ level: 1 }).run()"
          >H1</el-button>
        </el-tooltip>
        <el-tooltip content="标题 2" placement="bottom">
          <el-button
            :type="editor.isActive('heading', { level: 2 }) ? 'primary' : 'default'"
            size="small"
            @click="editor.chain().focus().toggleHeading({ level: 2 }).run()"
          >H2</el-button>
        </el-tooltip>
        <el-tooltip content="标题 3" placement="bottom">
          <el-button
            :type="editor.isActive('heading', { level: 3 }) ? 'primary' : 'default'"
            size="small"
            @click="editor.chain().focus().toggleHeading({ level: 3 }).run()"
          >H3</el-button>
        </el-tooltip>
      </div>

      <el-divider direction="vertical" />

      <div class="toolbar-group">
        <el-tooltip content="无序列表" placement="bottom">
          <el-button
            :type="editor.isActive('bulletList') ? 'primary' : 'default'"
            size="small"
            @click="editor.chain().focus().toggleBulletList().run()"
          ><el-icon><List /></el-icon></el-button>
        </el-tooltip>
        <el-tooltip content="有序列表" placement="bottom">
          <el-button
            :type="editor.isActive('orderedList') ? 'primary' : 'default'"
            size="small"
            @click="editor.chain().focus().toggleOrderedList().run()"
          >1.</el-button>
        </el-tooltip>
      </div>

      <el-divider direction="vertical" />

      <div class="toolbar-group">
        <el-tooltip content="引用" placement="bottom">
          <el-button
            :type="editor.isActive('blockquote') ? 'primary' : 'default'"
            size="small"
            @click="editor.chain().focus().toggleBlockquote().run()"
          ><el-icon><ChatLineRound /></el-icon></el-button>
        </el-tooltip>
        <el-tooltip content="代码块" placement="bottom">
          <el-button
            :type="editor.isActive('codeBlock') ? 'primary' : 'default'"
            size="small"
            @click="editor.chain().focus().toggleCodeBlock().run()"
          ><span style="font-family: monospace; font-weight: bold">{ }</span></el-button>
        </el-tooltip>
        <el-tooltip content="分割线" placement="bottom">
          <el-button
            size="small"
            @click="editor.chain().focus().setHorizontalRule().run()"
          >—</el-button>
        </el-tooltip>
      </div>

      <div style="flex: 1" />
    </div>

    <!-- Editor Content -->
    <div class="editor-body">
      <editor-content :editor="editor" class="editor-content" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { watch, onMounted, onUnmounted } from 'vue'
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

let autoSaveTimer: ReturnType<typeof setTimeout> | null = null
let lastSavedContent = ''
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

    // 自动保存：用户停 2 秒后才触发，不显示任何状态打扰输入
    if (autoSaveTimer) clearTimeout(autoSaveTimer)
    autoSaveTimer = setTimeout(() => {
      if (html !== lastSavedContent) {
        triggerSave(html)
      }
    }, 2000)
  },
})

watch(() => props.modelValue, (newVal) => {
  if (editor.value && newVal !== editor.value.getHTML()) {
    editor.value.commands.setContent(newVal || '', { emitUpdate: false })
    lastSavedContent = newVal || ''
  }
})

onMounted(() => {
  lastSavedContent = props.modelValue || ''
})

onUnmounted(() => {
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  editor.value?.destroy()
})

async function triggerSave(html: string, showToast?: boolean) {
  if (isSaving) return
  isSaving = true
  try {
    emit('save', props.noteId, html, showToast)
    lastSavedContent = html
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
  border-radius: 8px 8px 0 0;
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
  font-size: 13px;
}

.editor-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px;
}

:deep(.editor-content) {
  outline: none;
  min-height: 400px;
  font-size: 15.5px;
  line-height: 1.85;
  color: var(--rh-text-primary);
}

:deep(.editor-content:focus) {
  outline: none;
}

:deep(.ProseMirror) {
  outline: none;
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
  border-radius: 4px;
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
  border-radius: 0 8px 8px 0;
}

:deep(.ProseMirror hr) {
  border: none;
  border-top: 1px solid var(--rh-border-faint);
  margin: 24px 0;
}

:deep(.ProseMirror img) {
  max-width: 100%;
  border-radius: 8px;
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

:deep(.ProseMirror p.is-editor-empty:first-child::before) {
  content: attr(data-placeholder);
  float: left;
  color: var(--rh-text-placeholder);
  pointer-events: none;
  height: 0;
}

/* Save status */
.save-status {
  font-size: 12px;
  white-space: nowrap;
}

.status-saving {
  color: var(--rh-text-tertiary);
}

.status-saved {
  color: #10b981;
}

.status-error {
  color: var(--el-color-danger);
}
</style>

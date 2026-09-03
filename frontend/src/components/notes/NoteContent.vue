<template>
  <div class="note-content">
    <!-- Loading State -->
    <div v-if="notesLoading" class="center-state">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
    </div>

    <!-- Empty State: No folder selected -->
    <div v-else-if="!folderId" class="center-state empty-state">
      <el-icon :size="48" color="var(--rh-text-tertiary)"><FolderOpened /></el-icon>
      <p>请从左侧选择一个目录</p>
    </div>

    <!-- Empty State: Folder selected but no notes -->
    <div v-else-if="!selectedNote && notes.length === 0 && !isCreating" class="center-state empty-state">
      <el-icon :size="48" color="var(--rh-text-tertiary)"><Document /></el-icon>
      <p>该目录下还没有笔记</p>
      <div class="empty-actions">
        <el-button @click="triggerImport">
          <el-icon><Upload /></el-icon> 导入 MD
        </el-button>
        <el-button type="primary" @click="startCreate">创建第一篇笔记</el-button>
      </div>
    </div>

    <!-- Creating / Editing — 必须在列表条件之前，否则自动保存后 isCreating=false,isEditing=true 会被列表截胡 -->
    <div v-else-if="isCreating || isEditing" class="editor-view">
      <div class="editor-header">
        <div class="editor-header-left">
          <el-button text @click="cancelEdit">
            <el-icon><ArrowLeft /></el-icon> 退出编辑
          </el-button>
          <h2 class="editor-title">{{ isCreating ? '新建笔记' : '编辑笔记' }}</h2>
        </div>
        <div class="editor-header-right">
          <span class="editor-hint">Ctrl+S 保存</span>
          <el-button type="primary" size="small" @click="manualSave">
            <el-icon><Check /></el-icon> 保存
          </el-button>
        </div>
      </div>

      <div class="editor-meta-form">
        <el-input
          v-model="editTitle"
          placeholder="输入笔记标题..."
          size="large"
          class="title-input"
        />
        <div class="meta-row">
          <el-select
            v-model="editCategoryId"
            placeholder="选择目录（可选）"
            clearable
            size="small"
            class="category-select"
          >
            <el-option
              v-for="cat in flatCategories"
              :key="cat.id"
              :label="cat.name"
              :value="cat.id"
            />
          </el-select>
          <el-input
            v-model="editTags"
            placeholder="标签，逗号分隔"
            size="small"
            class="tags-input"
          />
        </div>
      </div>

      <WysiwygEditor
        ref="editorRef"
        v-model="editContent"
        :note-id="editingNoteId"
        @save="handleSave"
      />
    </div>

    <!-- Document List (folder selected, no note selected, not creating/editing) -->
    <div v-else-if="!selectedNote && !isCreating" class="note-list-view">
      <div class="list-header">
        <h2 class="list-title">{{ folderName }}</h2>
        <div class="list-actions">
          <el-button size="small" @click="triggerImport">
            <el-icon><Upload /></el-icon> 导入 MD
          </el-button>
          <el-button type="primary" size="small" @click="startCreate">
            <el-icon><Plus /></el-icon> 新建笔记
          </el-button>
        </div>
      </div>

      <div class="note-cards">
        <div
          v-for="note in notes"
          :key="note.id"
          class="note-card"
          @click="selectNote(note)"
          @contextmenu.prevent="showNoteContextMenu($event, note)"
        >
          <div class="card-header">
            <h3 class="card-title">
              <el-tag v-if="note.is_pinned" size="small" type="warning" class="pin-tag">置顶</el-tag>
              {{ note.title }}
            </h3>
          </div>
          <p class="card-preview">{{ note.content_preview || '暂无内容' }}</p>
          <div class="card-footer">
            <el-tag v-if="note.category_name" size="small" type="info">
              {{ note.category_name }}
            </el-tag>
            <el-tag
              v-for="tag in (note.tags || [])"
              :key="tag"
              size="small"
              class="note-tag"
            >{{ tag }}</el-tag>
            <span class="card-time">{{ formatTime(note.updated_at) }}</span>
          </div>
        </div>

        <!-- Pagination -->
        <div v-if="total > pageSize" class="pagination-wrapper">
          <el-pagination
            :current-page="page"
            :page-size="pageSize"
            :total="total"
            layout="prev, pager, next"
            small
            @current-change="handlePageChange"
          />
        </div>
      </div>
    </div>

    <!-- Reader Mode -->
    <div v-else-if="selectedNote && !isEditing" class="reader-view">
      <NoteReader
        :note="selectedNote"
        @back="clearSelection"
        @edit="startEdit"
        @delete="handleDelete"
        @toggle-pin="handleTogglePin"
      />
    </div>
  </div>

  <!-- Hidden file input for MD import -->
  <input
    ref="fileInputRef"
    type="file"
    accept=".md,.markdown"
    style="display: none"
    @change="handleFileImport"
  />

  <!-- Note Context Menu -->
  <teleport to="body">
    <ul
      v-if="noteContextMenu.visible"
      class="context-menu"
      :style="{ left: noteContextMenu.x + 'px', top: noteContextMenu.y + 'px' }"
    >
      <li @click="contextEdit">编辑</li>
      <li @click="contextTogglePin">{{ noteContextMenu.note?.is_pinned ? '取消置顶' : '置顶' }}</li>
      <li class="divider" />
      <li class="danger" @click="contextDelete">删除</li>
    </ul>
  </teleport>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Loading, FolderOpened, Document, Plus, ArrowLeft, Check, Upload,
} from '@element-plus/icons-vue'
import MarkdownIt from 'markdown-it'
import { useNotesStore } from '../../stores/notes'
import { useCategoriesStore } from '../../stores/categories'
import type { Note } from '../../api/notes'
import NoteReader from './NoteReader.vue'
import WysiwygEditor from './WysiwygEditor.vue'

const props = defineProps<{
  folderId: number | null
}>()

const notesStore = useNotesStore()
const categoriesStore = useCategoriesStore()

const md = new MarkdownIt({ html: false })

// State
const selectedNote = ref<Note | null>(null)
const isCreating = ref(false)
const isEditing = ref(false)
const editTitle = ref('')
const editContent = ref('')
const editCategoryId = ref<number | null>(null)
const editTags = ref('')
const editingNoteId = ref<number | undefined>(undefined)
const editorRef = ref<InstanceType<typeof WysiwygEditor>>()
const fileInputRef = ref<HTMLInputElement>()

// Computed
const notes = computed(() => notesStore.notes)
const total = computed(() => notesStore.total)
const page = computed(() => notesStore.page)
const pageSize = computed(() => notesStore.pageSize)
const notesLoading = computed(() => notesStore.loading)

const flatCategories = computed(() => {
  const flatten = (items: any[]): any[] => {
    const result: any[] = []
    for (const item of items) {
      result.push(item)
      if (item.children?.length) result.push(...flatten(item.children))
    }
    return result
  }
  return flatten(categoriesStore.noteCategories)
})

// Note context menu
const noteContextMenu = reactive({
  visible: false,
  x: 0,
  y: 0,
  note: null as Note | null,
})

const folderName = computed(() => {
  for (const cat of categoriesStore.noteCategories) {
    const found = findCategory(cat, props.folderId)
    if (found) return found.name
  }
  return '笔记'
})

function findCategory(cat: any, id: number | null): any {
  if (cat.id === id) return cat
  if (cat.children) {
    for (const child of cat.children) {
      const found = findCategory(child, id)
      if (found) return found
    }
  }
  return null
}

// Watch folder changes → fetch notes
watch(() => props.folderId, (newId) => {
  if (newId) {
    notesStore.setCategory(newId)
    clearSelection()
  } else {
    notesStore.notes = []
    notesStore.total = 0
  }
}, { immediate: true })

async function selectNote(note: Note) {
  isCreating.value = false
  isEditing.value = false
  // 从 API 获取完整内容（列表接口不返回 content 字段）
  try {
    await notesStore.fetchNote(note.id)
    selectedNote.value = notesStore.currentNote
  } catch {
    ElMessage.error('无法加载笔记')
    selectedNote.value = null
  }
}

function clearSelection() {
  selectedNote.value = null
  isCreating.value = false
  isEditing.value = false
  notesStore.fetchNotes() // 回到列表时刷新
}

function startCreate() {
  isCreating.value = true
  isEditing.value = false
  selectedNote.value = null
  editingNoteId.value = undefined
  editTitle.value = ''
  editContent.value = ''
  editCategoryId.value = props.folderId
  editTags.value = ''
}

function triggerImport() {
  fileInputRef.value?.click()
}

async function handleFileImport(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  const title = file.name.replace(/\.(md|markdown)$/i, '')
  const content = await file.text()

  try {
    await notesStore.createNote({
      title,
      content,
      category_id: props.folderId,
      tags: [],
    })
    ElMessage.success(`已导入「${title}」`)
    notesStore.fetchNotes()
  } catch {
    ElMessage.error('导入失败')
  }

  // Reset input so same file can be re-imported
  input.value = ''
}

function startEdit() {
  if (!selectedNote.value) return
  isEditing.value = true
  isCreating.value = false
  editingNoteId.value = selectedNote.value.id
  editTitle.value = selectedNote.value.title
  editCategoryId.value = selectedNote.value.category_id

  const raw = selectedNote.value.content || ''
  editContent.value = isHtml(raw) ? raw : md.render(raw)
  editTags.value = (selectedNote.value.tags || []).join(', ')

  nextTick(() => {
    editorRef.value?.manualSave?.()
  })
}

function cancelEdit() {
  if (isCreating.value) {
    isCreating.value = false
  } else {
    isEditing.value = false
  }
  // 退出编辑时刷新列表，使新创建的笔记/修改的标题立即显示
  notesStore.fetchNotes()
}

function isHtml(str: string): boolean {
  return /<[a-z][\s\S]*>/i.test(str)
}

async function handleSave(noteId: number | undefined, content: string, showToast?: boolean) {
  if (!editTitle.value.trim()) {
    ElMessage.warning('请输入标题')
    return
  }

  const tags = editTags.value
    .split(',')
    .map((t) => t.trim())
    .filter((t) => t)

  const data = {
    title: editTitle.value.trim(),
    content,
    category_id: editCategoryId.value,
    tags,
  }

  if (noteId) {
    const updated = await notesStore.updateNote(noteId, data)
    editingNoteId.value = noteId
    // 同步更新 selectedNote，退出编辑后阅读模式显示最新内容
    if (selectedNote.value?.id === noteId) {
      selectedNote.value = updated
    }
  } else {
    const created = await notesStore.createNote(data)
    // Capture the new note's ID so subsequent auto-saves use updateNote, not createNote
    editingNoteId.value = created.id
    isCreating.value = false
    isEditing.value = true
  }
  if (showToast) ElMessage.success('已保存')
}

function manualSave() {
  editorRef.value?.manualSave?.()
}

function handleKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    e.preventDefault()
    manualSave()
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
  document.addEventListener('click', closeNoteContextMenu)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
  document.removeEventListener('click', closeNoteContextMenu)
})

async function handleDelete(id: number) {
  await notesStore.deleteNote(id)
  selectedNote.value = null
  await notesStore.fetchNotes() // 删除后刷新列表
  ElMessage.success('已删除')
}

async function handleTogglePin(id: number) {
  await notesStore.togglePin(id)
}

function handlePageChange(p: number) {
  notesStore.setPage(p)
}

function showNoteContextMenu(e: MouseEvent, note: Note) {
  noteContextMenu.visible = true
  noteContextMenu.x = e.clientX
  noteContextMenu.y = e.clientY
  noteContextMenu.note = note
}

function closeNoteContextMenu() {
  noteContextMenu.visible = false
}

function contextEdit() {
  const note = noteContextMenu.note
  noteContextMenu.visible = false
  if (!note) return
  selectNote(note)
  nextTick(() => startEdit())
}

async function contextTogglePin() {
  const note = noteContextMenu.note
  noteContextMenu.visible = false
  if (!note) return
  await notesStore.togglePin(note.id)
  ElMessage.success(note.is_pinned ? '已取消置顶' : '已置顶')
  notesStore.fetchNotes()
}

async function contextDelete() {
  const note = noteContextMenu.note
  noteContextMenu.visible = false
  if (!note) return
  await handleDelete(note.id)
}

function formatTime(dateStr: string) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>

<style>
/* Context menu — not scoped because teleported to body */
.context-menu {
  position: fixed;
  z-index: 9999;
  list-style: none;
  margin: 0;
  padding: 6px 0;
  background: var(--rh-bg-card);
  border-radius: var(--rh-radius-sm);
  box-shadow: var(--rh-shadow-lg);
  min-width: 140px;
  border: 1px solid var(--rh-border);
}

.context-menu li {
  padding: 8px 16px;
  font-size: 13px;
  cursor: pointer;
  color: var(--rh-text-primary);
  transition: background-color var(--rh-duration-fast) var(--rh-transition-fast);
}

.context-menu li:hover {
  background: var(--rh-bg-hover);
}

.context-menu li.danger {
  color: var(--rh-danger);
}

.context-menu li.divider {
  padding: 0;
  height: 1px;
  background: var(--rh-border-faint);
  margin: 4px 0;
  cursor: default;
}

.context-menu li.divider:hover {
  background: var(--rh-border-faint);
}
</style>

<style scoped>
.note-content {
  height: 100%;
  overflow-y: auto;
}

/* Center states */
.center-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 400px;
  gap: 16px;
  color: var(--rh-text-tertiary);
}

.center-state p {
  font-size: 15px;
  margin: 0;
}

.empty-actions {
  display: flex;
  gap: 12px;
}

/* Document List */
.note-list-view {
  padding: 24px 32px;
  max-width: 900px;
  margin: 0 auto;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.list-actions {
  display: flex;
  gap: 8px;
}

.list-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--rh-text-primary);
  margin: 0;
}

.note-cards {
  display: flex;
  flex-direction: column;
}

.note-card {
  padding: 14px 20px;
  border-bottom: 1px solid var(--rh-border-faint);
  cursor: pointer;
  transition: border-color var(--rh-duration-normal) var(--rh-transition-normal),
              background-color var(--rh-duration-fast) var(--rh-transition-fast);
  border-radius: var(--rh-radius-xs);
}

.note-card:hover {
  background: var(--rh-bg-hover);
}

.note-card:last-child {
  border-bottom: none;
}

.card-header {
  margin-bottom: 6px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--rh-text-primary);
  margin: 0;
  display: flex;
  align-items: center;
  gap: 6px;
}

.pin-tag {
  flex-shrink: 0;
}

.card-preview {
  font-size: 13px;
  color: var(--rh-text-secondary);
  line-height: 1.5;
  margin-bottom: 10px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.card-footer {
  display: flex;
  gap: 6px;
  align-items: center;
  flex-wrap: wrap;
}

.note-tag {
  margin-right: 2px;
}

.card-time {
  margin-left: auto;
  font-size: 12px;
  color: var(--rh-text-tertiary);
  white-space: nowrap;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  padding: 20px 0 8px;
  border-top: 1px solid var(--rh-border-faint);
  margin-top: 8px;
}

/* Editor View */
.editor-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  border-bottom: 1px solid var(--rh-border-faint);
  transition: border-color var(--rh-duration-normal) var(--rh-transition-normal);
}

.editor-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.editor-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.editor-hint {
  font-size: 12px;
  color: var(--rh-text-tertiary);
  white-space: nowrap;
}

.editor-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--rh-text-primary);
  margin: 0;
}

.editor-meta-form {
  padding: 16px 16px 0;
  max-width: 800px;
}

.title-input {
  margin-bottom: 10px;
}

.meta-row {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}

.category-select {
  width: 200px;
}

.tags-input {
  flex: 1;
}

/* Reader View */
.reader-view {
  height: 100%;
  overflow-y: auto;
}
</style>

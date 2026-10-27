<template>
  <div class="note-content">
    <!-- Loading State -->
    <LoadingState v-if="notesLoading" variant="card" />

    <!-- Empty State: No folder selected -->
    <EmptyState
      v-else-if="!folderId && !notesStore.selectedTag"
      :icon="FolderOpened"
      title="请先选择一个目录"
    />

    <!-- Empty State: Folder selected but no notes -->
    <EmptyState
      v-else-if="!selectedNote && notes.length === 0 && !isCreating"
      :icon="Document"
      title="该目录下还没有笔记"
    >
      <el-button @click="triggerImport">
        <el-icon><Upload /></el-icon> 导入 MD
      </el-button>
      <el-button :loading="isImportingFolder" @click="triggerFolderImport">
        <el-icon><Folder /></el-icon> 导入文件夹
      </el-button>
      <span v-if="isImportingFolder" class="import-progress">{{ importProgress }}</span>
      <el-button type="primary" @click="startCreate">创建第一篇笔记</el-button>
    </EmptyState>

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
          <span class="editor-hint" :class="`is-${saveStatus}`" aria-live="polite">{{ saveStatusText }}</span>
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
          <el-select
            v-model="editTags"
            multiple
            filterable
            allow-create
            default-first-option
            :reserve-keyword="false"
            placeholder="标签（回车添加）"
            size="small"
            class="tags-input"
            aria-label="笔记标签"
          >
            <el-option v-for="tag in allNoteTags" :key="tag" :label="tag" :value="tag" />
          </el-select>
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
          <el-button size="small" :loading="isImportingFolder" @click="triggerFolderImport">
            <el-icon><Folder /></el-icon> 导入文件夹
          </el-button>
          <span v-if="isImportingFolder" class="import-progress">{{ importProgress }}</span>
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
              <el-tag v-if="note.is_pinned" size="small" class="pin-tag">置顶</el-tag>
              {{ note.title }}
            </h3>
            <!-- 右键菜单的键盘 / 触屏等价入口 -->
            <button
              type="button"
              class="card-more"
              :aria-label="`「${note.title}」的更多操作`"
              @click.stop="showNoteActions($event, note)"
            >
              <el-icon><MoreFilled /></el-icon>
            </button>
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
            <span class="card-time">{{ formatRelative(note.updated_at) }}</span>
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
        :publishing="publishing"
        @back="clearSelection"
        @edit="startEdit"
        @delete="handleDelete"
        @toggle-pin="handleTogglePin"
        @toggle-publish="handleTogglePublish"
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
  <input
    ref="folderInputRef"
    type="file"
    accept=".md,.markdown"
    webkitdirectory
    directory
    multiple
    style="display: none"
    @change="handleFolderImport"
  />

  <!-- Note Context Menu -->
  <teleport to="body">
    <ul
      v-if="noteContextMenu.visible"
      class="context-menu animate-scale-in"
      role="menu"
      :style="{ left: noteContextMenu.x + 'px', top: noteContextMenu.y + 'px' }"
      @keydown.escape="closeNoteContextMenu()"
    >
      <li role="menuitem" tabindex="-1" @click="contextEdit">编辑</li>
      <li role="menuitem" tabindex="-1" @click="contextTogglePin">{{ noteContextMenu.note?.is_pinned ? '取消置顶' : '置顶' }}</li>
      <li class="divider" role="separator" aria-hidden="true" />
      <li role="menuitem" tabindex="-1" class="danger" @click="contextDelete">删除</li>
    </ul>
  </teleport>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  FolderOpened, Folder, Document, Plus, ArrowLeft, Check, Upload, MoreFilled,
} from '@element-plus/icons-vue'
import MarkdownIt from 'markdown-it'
import { notesApi } from '../../api/notes'
import { plazaApi } from '../../api/plaza'
import { useNotesStore } from '../../stores/notes'
import { useCategoriesStore } from '../../stores/categories'
import type { Note } from '../../api/notes'
import NoteReader from './NoteReader.vue'
import WysiwygEditor from './WysiwygEditor.vue'
import { formatRelative } from '../../utils/format'
import EmptyState from '../common/EmptyState.vue'
import LoadingState from '../common/LoadingState.vue'

const props = defineProps<{
  folderId: number | null
  noteId?: number | null
}>()

const emit = defineEmits<{
  'update:noteId': [id: number | null]
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
/** 标签与提示词模块统一为数组 + 可选可建，避免"逗号分隔字符串"两套心智 */
const editTags = ref<string[]>([])
const editingNoteId = ref<number | undefined>(undefined)
const editorRef = ref<InstanceType<typeof WysiwygEditor>>()
const fileInputRef = ref<HTMLInputElement>()
const folderInputRef = ref<HTMLInputElement>()
const isImportingFolder = ref(false)
const importProgress = ref('')
/** 未保存内容标记 + 保存状态提示（原先保存过程对用户完全不可见） */
const isDirty = ref(false)
const saveStatus = ref<'idle' | 'saving' | 'saved' | 'error'>('idle')
const lastSavedAt = ref<Date | null>(null)
let autoSaveTimer: ReturnType<typeof setTimeout> | null = null

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

/** 已有标签集合：用于标签选择器的候选与提示，避免用户手工输入非法值 */
const allNoteTags = computed(() => {
  const set = new Set<string>()
  for (const note of notesStore.allNotes.length ? notesStore.allNotes : notesStore.notes) {
    for (const tag of note.tags || []) set.add(tag)
  }
  return [...set].sort()
})

/** 保存状态文案（编辑器头部展示，随状态与时间变化） */
const saveStatusText = computed(() => {
  const shortcut = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent) ? '⌘S' : 'Ctrl+S'
  if (saveStatus.value === 'saving') return '正在保存...'
  if (saveStatus.value === 'error') return '保存失败，请手动保存'
  if (saveStatus.value === 'saved' && lastSavedAt.value) {
    const time = `${String(lastSavedAt.value.getHours()).padStart(2, '0')}:${String(lastSavedAt.value.getMinutes()).padStart(2, '0')}`
    return `已保存 ${time}`
  }
  return `${shortcut} 保存`
})

/** 记录未保存状态，并安排防抖自动保存 */
function markDirty() {
  if (!isEditing.value && !isCreating.value) return
  isDirty.value = true
  if (saveStatus.value !== 'saving') saveStatus.value = 'idle'
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  autoSaveTimer = setTimeout(() => { void autoSave() }, 1500)
}

/** 内容有变化时静默保存；标题为空时不触发，避免产生空笔记 */
async function autoSave() {
  if (!isDirty.value) return
  if (!editTitle.value.trim()) return
  if (!editContent.value.trim()) return
  try {
    await handleSave(editingNoteId.value, editContent.value)
    markSaved()
  } catch {
    saveStatus.value = 'error'
  }
}

function markSaved() {
  isDirty.value = false
  saveStatus.value = 'saved'
  lastSavedAt.value = new Date()
}

// 编辑内容 / 标题 / 标签 / 目录任一变化都视为未保存
watch([editContent, editTitle, editTags, editCategoryId], () => markDirty())

// Note context menu
const noteContextMenu = reactive({
  visible: false,
  x: 0,
  y: 0,
  note: null as Note | null,
})

const folderName = computed(() => {
  // 标签过滤视图（Dashboard 标签云跳转）优先展示标签名
  if (notesStore.selectedTag) return `标签：${notesStore.selectedTag}`
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

// Watch folder changes → fetch notes（阅读态由 noteId 驱动，此处不再清除选中）
watch(() => props.folderId, (newId) => {
  if (newId) {
    notesStore.setCategory(newId)
  } else if (!notesStore.selectedTag) {
    // 标签过滤视图（无目录）保留已拉取的列表，不清空
    notesStore.notes = []
    notesStore.total = 0
  }
}, { immediate: true })

// 加载并进入阅读模式（列表接口不返回 content，需按 id 拉全文）
async function openNote(id: number) {
  isCreating.value = false
  isEditing.value = false
  try {
    await notesStore.fetchNote(id)
    selectedNote.value = notesStore.currentNote
  } catch {
    ElMessage.error('无法加载笔记')
    selectedNote.value = null
  }
}

// Watch external note selection（目录树点击笔记叶子节点）
watch(() => props.noteId, (newId) => {
  if (newId == null) {
    selectedNote.value = null
    isCreating.value = false
    isEditing.value = false
    return
  }
  openNote(newId)
}, { immediate: true })

function selectNote(note: Note) {
  emit('update:noteId', note.id)
}

function clearSelection() {
  emit('update:noteId', null)
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
  editTags.value = []
  // 清空字段会触发 watch → markDirty，等 watch 回调后再复位脏标记
  nextTick(() => {
    isDirty.value = false
    saveStatus.value = 'idle'
  })
}

function triggerImport() {
  fileInputRef.value?.click()
}

function triggerFolderImport() {
  if (!props.folderId || isImportingFolder.value) return
  folderInputRef.value?.click()
}

async function handleFileImport(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  const title = file.name.replace(/\.(md|markdown)$/i, '')
  const content = await file.text()

  try {
    await notesApi.importOrReplace({
      title,
      content,
      category_id: props.folderId,
      tags: [],
    })
    ElMessage.success(`已导入「${title}」`)
    notesStore.fetchNotes()
    notesStore.fetchAllNotes() // 同步目录树的笔记叶子节点
  } catch {
    ElMessage.error('导入失败')
  }

  // Reset input so same file can be re-imported
  input.value = ''
}

type ImportFile = File & { webkitRelativePath?: string }

async function handleFolderImport(e: Event) {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files || []) as ImportFile[]
  input.value = ''
  if (!files.length || !props.folderId) return

  const markdownFiles = files.filter((file) => /\.(md|markdown)$/i.test(file.name))
  if (!markdownFiles.length) {
    ElMessage.warning('所选文件夹中没有 Markdown 文件')
    return
  }

  isImportingFolder.value = true
  const categoryCache = new Map<string, number>()
  const findExistingCategory = (parentId: number | null, name: string) => {
    const walk = (items: any[]): number | null => {
      for (const item of items) {
        if (item.parent_id === parentId && item.name === name) return item.id
        const found = walk(item.children || [])
        if (found) return found
      }
      return null
    }
    return walk(categoriesStore.noteCategories)
  }

  const ensureCategoryPath = async (segments: string[]) => {
    let parentId = props.folderId as number
    const pathParts: string[] = []
    for (const name of segments) {
      pathParts.push(name)
      const pathKey = pathParts.join('/')
      const cached = categoryCache.get(pathKey)
      if (cached) {
        parentId = cached
        continue
      }
      const existing = findExistingCategory(parentId, name)
      const categoryId = existing ?? (await categoriesStore.createCategory({
        name,
        type: 'note',
        parent_id: parentId,
      })).id
      categoryCache.set(pathKey, categoryId)
      parentId = categoryId
    }
    return parentId
  }

  let imported = 0
  try {
    for (const file of markdownFiles) {
      const relativePath = file.webkitRelativePath || file.name
      const pathSegments = relativePath.split(/[\\/]/).filter(Boolean)
      const folderSegments = pathSegments.slice(0, -1)
      const categoryId = await ensureCategoryPath(folderSegments)
      const title = file.name.replace(/\.(md|markdown)$/i, '')
      importProgress.value = `正在导入 ${imported + 1}/${markdownFiles.length}`
      await notesApi.importOrReplace({
        title,
        content: await file.text(),
        category_id: categoryId,
        tags: [],
      })
      imported += 1
    }
    await categoriesStore.fetchCategories('note')
    await notesStore.fetchNotes()
    await notesStore.fetchAllNotes() // 同步目录树
    ElMessage.success(`已导入 ${imported} 篇笔记，目录层级已保留`)
  } catch {
    ElMessage.error(`导入中断，已完成 ${imported} 篇笔记`)
    await categoriesStore.fetchCategories('note')
    await notesStore.fetchNotes()
    await notesStore.fetchAllNotes()
  } finally {
    isImportingFolder.value = false
    importProgress.value = ''
  }
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
  editTags.value = [...(selectedNote.value.tags || [])]
  // 载入内容会触发 watch → markDirty，需等 watch 回调执行后再复位脏标记，避免刚打开就判定未保存
  nextTick(() => {
    isDirty.value = false
    saveStatus.value = 'idle'
  })
}

/** 退出编辑：存在未保存修改时先确认，避免内容静默丢失 */
async function cancelEdit() {
  if (isDirty.value) {
    try {
      await ElMessageBox.confirm('当前修改尚未保存，确定退出编辑吗？', '未保存的修改', {
        confirmButtonText: '放弃修改',
        cancelButtonText: '继续编辑',
        type: 'warning',
      })
    } catch {
      return
    }
  }
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  isDirty.value = false
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

  const tags = editTags.value.map((t) => t.trim()).filter((t) => t)

  const data = {
    title: editTitle.value.trim(),
    content,
    category_id: editCategoryId.value,
    tags,
  }

  saveStatus.value = 'saving'
  try {
    if (noteId) {
      const updated = await notesStore.updateNote(noteId, data)
      editingNoteId.value = noteId
      // 同步更新 selectedNote，退出编辑后阅读模式显示最新内容
      if (selectedNote.value?.id === noteId) {
        selectedNote.value = updated
      }
    } else {
      const created = await notesStore.createNote(data)
      // 记录新建笔记的 ID，后续自动保存走 updateNote 而不是重复创建
      editingNoteId.value = created.id
      isCreating.value = false
      isEditing.value = true
    }
    if (showToast) ElMessage.success('已保存')
    markSaved()
  } catch (error) {
    saveStatus.value = 'error'
    throw error
  }
}

function manualSave() {
  editorRef.value?.manualSave?.()
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && noteContextMenu.visible) {
    closeNoteContextMenu()
    return
  }
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    e.preventDefault()
    manualSave()
  }
}

/** 离开页面或关闭标签页时拦截未保存的修改 */
function handleBeforeUnload(e: BeforeUnloadEvent) {
  if (!isDirty.value) return
  e.preventDefault()
  e.returnValue = ''
}

onBeforeRouteLeave(async () => {
  if (!isDirty.value) return true
  try {
    await ElMessageBox.confirm('当前修改尚未保存，确定离开吗？', '未保存的修改', {
      confirmButtonText: '放弃修改',
      cancelButtonText: '继续编辑',
      type: 'warning',
    })
    if (autoSaveTimer) clearTimeout(autoSaveTimer)
    isDirty.value = false
    return true
  } catch {
    return false
  }
})

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
  document.addEventListener('click', closeNoteContextMenu)
  window.addEventListener('beforeunload', handleBeforeUnload)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
  document.removeEventListener('click', closeNoteContextMenu)
  window.removeEventListener('beforeunload', handleBeforeUnload)
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
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

const publishing = ref(false)

async function handleTogglePublish() {
  const note = selectedNote.value
  if (!note) return
  publishing.value = true
  try {
    const isPublic = note.visibility === 'public'
    if (isPublic) {
      await plazaApi.unpublish('note', note.id)
      note.visibility = 'private'
      ElMessage.success('已从资源广场取消发布')
    } else {
      await plazaApi.publish('note', note.id)
      note.visibility = 'public'
      ElMessage.success('已发布到资源广场，团队成员可见')
    }
  } catch {
    ElMessage.error('操作失败')
  } finally {
    publishing.value = false
  }
}

function handlePageChange(p: number) {
  notesStore.setPage(p)
}

function showNoteContextMenu(e: MouseEvent, note: Note) {
  openNoteMenu(e.clientX, e.clientY, note)
}

/** 「⋯」按钮入口：复用同一套菜单，定位到按钮处 */
function showNoteActions(e: MouseEvent, note: Note) {
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  openNoteMenu(rect.right, rect.bottom + 4, note)
}

/** 菜单定位时防止越出视口，保证贴边时仍可完整点击 */
function openNoteMenu(x: number, y: number, note: Note) {
  const MENU_WIDTH = 160
  const MENU_HEIGHT = 132
  noteContextMenu.visible = true
  noteContextMenu.x = Math.min(x, window.innerWidth - MENU_WIDTH - 8)
  noteContextMenu.y = Math.min(y, window.innerHeight - MENU_HEIGHT - 8)
  noteContextMenu.note = note
}

function closeNoteContextMenu() {
  noteContextMenu.visible = false
}

async function contextEdit() {
  const note = noteContextMenu.note
  noteContextMenu.visible = false
  if (!note) return
  await openNote(note.id)
  startEdit()
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
</script>

<style scoped>
.note-content {
  height: 100%;
  overflow-y: auto;
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
  align-items: center;
}

.import-progress {
  font-size: 12px;
  color: var(--rh-text-tertiary);
  white-space: nowrap;
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
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}

/* 右键菜单的键盘 / 触屏等价入口：「⋯」按钮默认隐藏，悬停或键盘聚焦时显现 */
.card-more {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  margin: -6px -8px 0 0;
  padding: 0;
  border: none;
  border-radius: var(--rh-radius-sm);
  background: transparent;
  color: var(--rh-text-tertiary);
  cursor: pointer;
  opacity: 0;
  transition: var(--rh-transition-all-fast);
}

.note-card:hover .card-more,
.card-more:focus-visible {
  opacity: 1;
}

.card-more:hover {
  background: var(--rh-bg-active);
  color: var(--rh-text-primary);
}

/* 触屏 / 无悬停设备上始终可见，否则用户无法唤出菜单 */
@media (hover: none) {
  .card-more {
    opacity: 1;
  }
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
  transition: color var(--rh-duration-fast) var(--rh-transition-fast);
}

.editor-hint.is-saving {
  color: var(--rh-text-secondary);
}

.editor-hint.is-saved {
  color: var(--rh-success-strong);
}

.editor-hint.is-error {
  color: var(--rh-danger);
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
  min-width: 0;
}

/* Reader View */
.reader-view {
  height: 100%;
  overflow-y: auto;
}

/* 笔记右键菜单（teleport 到 body；scoped 属性随节点一并迁移，仍可生效） */
.context-menu {
  position: fixed;
  z-index: var(--rh-z-popover);
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

.context-menu li:hover,
.context-menu li:focus-visible {
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

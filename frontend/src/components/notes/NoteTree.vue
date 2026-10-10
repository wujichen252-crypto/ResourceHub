<template>
  <div class="note-tree">
    <div class="tree-header">
      <span class="tree-title">目录</span>
      <el-button text size="small" @click="handleAddRootFolder">
        <el-icon><Plus /></el-icon>
      </el-button>
    </div>

    <el-tree
      ref="treeRef"
      :data="treeData"
      :props="{ children: 'children', label: 'name' }"
      node-key="id"
      :current-node-key="currentNodeKey"
      :default-expanded-keys="expandedKeys"
      :expand-on-click-node="false"
      highlight-current
      @node-click="handleNodeClick"
      @node-contextmenu="handleContextMenu"
      @node-expand="handleNodeExpand"
      @node-collapse="handleNodeCollapse"
      class="category-tree"
    >
      <template #default="{ data }">
        <span class="tree-node">
          <el-icon class="folder-icon" :class="{ 'note-icon': data.isNote }">
            <Document v-if="data.isNote" />
            <FolderOpened v-else />
          </el-icon>
          <span class="node-label" :class="{ 'note-label': data.isNote }">{{ data.name }}</span>
        </span>
      </template>
    </el-tree>

    <!-- Context Menu with scaleIn Animation -->
    <teleport to="body">
      <Transition name="scaleIn" @after-leave="closeContextMenu">
        <ul
          v-if="contextMenu.visible"
          class="context-menu animate-scale-in"
          :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
        >
        <li @click="handleAddSubFolder">新建子目录</li>
        <li @click="handleRename">重命名</li>
        <li class="divider" />
        <li class="danger" @click="handleDelete">删除</li>
        </ul>
      </Transition>
    </teleport>

    <!-- Rename Dialog -->
    <el-dialog
      v-model="renameDialog.visible"
      title="重命名目录"
      width="320px"
      :close-on-click-modal="false"
    >
      <el-input
        v-model="renameDialog.name"
        placeholder="请输入新名称"
        @keyup.enter="confirmRename"
      />
      <template #footer>
        <el-button @click="renameDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="confirmRename">确定</el-button>
      </template>
    </el-dialog>

    <!-- New Folder Dialog -->
    <el-dialog
      v-model="newFolderDialog.visible"
      title="新建子目录"
      width="320px"
      :close-on-click-modal="false"
    >
      <el-input
        v-model="newFolderDialog.name"
        placeholder="请输入目录名称"
        @keyup.enter="confirmNewFolder"
      />
      <template #footer>
        <el-button @click="newFolderDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="confirmNewFolder">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted, onUnmounted } from 'vue'
import { Plus, FolderOpened, Document } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { ElTree } from 'element-plus'
import { useCategoriesStore } from '../../stores/categories'
import { useNotesStore } from '../../stores/notes'
import type { CategoryTreeNode } from '../../api/categories'

// 树节点：分类 + 笔记两级混合（笔记为叶子节点）
interface TreeNode {
  id: string            // 唯一 key：cat-{id} / note-{id}，避免分类与笔记 id 冲突
  name: string
  isNote: boolean
  categoryId?: number   // 分类节点原始 id
  noteId?: number       // 笔记节点原始 id
  children?: TreeNode[]
}

const props = defineProps<{
  modelValue: number | null
  selectedNoteId?: number | null
}>()

const emit = defineEmits<{
  'update:modelValue': [id: number | null]
  'select-note': [noteId: number]
}>()

const categoriesStore = useCategoriesStore()
const notesStore = useNotesStore()
const treeRef = ref<InstanceType<typeof ElTree>>()

// 展开状态 — 数据刷新后恢复，避免折叠（存分类节点 key：cat-{id}）
const expandedKeys = ref<string[]>([])

const currentNodeKey = computed(() => {
  if (props.selectedNoteId) return `note-${props.selectedNoteId}`
  if (props.modelValue) return `cat-${props.modelValue}`
  return null
})

// 将分类树与全量笔记合并：每个分类节点的 children = 子分类 + 该分类下的笔记
const treeData = computed<TreeNode[]>(() => {
  const notesByCategory = new Map<number, TreeNode[]>()
  for (const note of notesStore.allNotes) {
    if (note.category_id == null) continue
    if (!notesByCategory.has(note.category_id)) {
      notesByCategory.set(note.category_id, [])
    }
    notesByCategory.get(note.category_id)!.push({
      id: `note-${note.id}`,
      name: note.title,
      isNote: true,
      noteId: note.id,
    })
  }

  const mapCategory = (cat: CategoryTreeNode): TreeNode => {
    const subCats = (cat.children || []).map(mapCategory)
    const catNotes = notesByCategory.get(cat.id) || []
    return {
      id: `cat-${cat.id}`,
      name: cat.name,
      isNote: false,
      categoryId: cat.id,
      children: [...subCats, ...catNotes],
    }
  }
  return categoriesStore.noteCategories.map(mapCategory)
})

// Context menu state（仅分类节点支持右键菜单）
const contextMenu = reactive({
  visible: false,
  x: 0,
  y: 0,
  data: null as TreeNode | null,
})

// Dialog states
const renameDialog = reactive({
  visible: false,
  name: '',
  id: 0,
})
const newFolderDialog = reactive({
  visible: false,
  name: '',
  parentId: 0,
})
const isCreatingFolder = ref(false)

onMounted(() => {
  categoriesStore.fetchCategories('note')
  notesStore.fetchAllNotes()
  document.addEventListener('click', closeContextMenu)
})

onUnmounted(() => {
  document.removeEventListener('click', closeContextMenu)
})

function closeContextMenu() {
  contextMenu.visible = false
}

function handleNodeClick(data: TreeNode) {
  if (data.isNote && data.noteId != null) {
    emit('select-note', data.noteId)
  } else if (data.categoryId != null) {
    emit('update:modelValue', data.categoryId)
  }
}

function handleNodeExpand(data: TreeNode) {
  if (!expandedKeys.value.includes(data.id)) {
    expandedKeys.value.push(data.id)
  }
}

function handleNodeCollapse(data: TreeNode) {
  expandedKeys.value = expandedKeys.value.filter((k) => k !== data.id)
}

function handleContextMenu(
  _evt: MouseEvent,
  data: TreeNode,
  _node: unknown,
) {
  // 笔记叶子节点不提供目录管理菜单
  if (data.isNote) return
  contextMenu.visible = true
  contextMenu.x = _evt.clientX
  contextMenu.y = _evt.clientY
  contextMenu.data = data
}

async function handleAddRootFolder() {
  newFolderDialog.parentId = 0
  newFolderDialog.name = ''
  newFolderDialog.visible = true
}

function handleAddSubFolder() {
  contextMenu.visible = false
  if (!contextMenu.data?.categoryId) return
  newFolderDialog.parentId = contextMenu.data.categoryId
  newFolderDialog.name = ''
  newFolderDialog.visible = true
}

async function confirmNewFolder() {
  if (isCreatingFolder.value) return // 防止重复提交
  if (!newFolderDialog.name.trim()) {
    ElMessage.warning('请输入目录名称')
    return
  }
  isCreatingFolder.value = true
  try {
    // 先记录展开状态（createCategory 内部会 fetch 刷新树，导致折叠）
    const parentKey = `cat-${newFolderDialog.parentId}`
    if (newFolderDialog.parentId && !expandedKeys.value.includes(parentKey)) {
      expandedKeys.value.push(parentKey)
    }
    await categoriesStore.createCategory({
      name: newFolderDialog.name.trim(),
      type: 'note',
      parent_id: newFolderDialog.parentId || null,
    })
    // categoriesStore.createCategory 内部已调用 fetchCategories 刷新树
    ElMessage.success('目录创建成功')
    newFolderDialog.visible = false
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.msg || '创建失败')
  } finally {
    isCreatingFolder.value = false
  }
}

function handleRename() {
  contextMenu.visible = false
  if (!contextMenu.data?.categoryId) return
  renameDialog.id = contextMenu.data.categoryId
  renameDialog.name = contextMenu.data.name
  renameDialog.visible = true
}

async function confirmRename() {
  if (isCreatingFolder.value) return
  if (!renameDialog.name.trim()) {
    ElMessage.warning('请输入名称')
    return
  }
  isCreatingFolder.value = true
  try {
    await categoriesStore.updateCategory(renameDialog.id, {
      name: renameDialog.name.trim(),
    }, 'note')
    ElMessage.success('重命名成功')
    renameDialog.visible = false
    await categoriesStore.fetchCategories('note')
  } catch {
    ElMessage.error('重命名失败')
  } finally {
    isCreatingFolder.value = false
  }
}

async function handleDelete() {
  if (isCreatingFolder.value) return
  contextMenu.visible = false
  const categoryId = contextMenu.data?.categoryId
  if (!categoryId) return

  try {
    await ElMessageBox.confirm(
      `确定要删除「${contextMenu.data!.name}」及其所有子目录和笔记吗？此操作不可恢复。`,
      '确认删除',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' },
    )
    isCreatingFolder.value = true
    await categoriesStore.deleteCategory(categoryId, 'note')
    ElMessage.success('已删除')
    if (props.modelValue === categoryId) {
      emit('update:modelValue', null)
    }
    await categoriesStore.fetchCategories('note')
    await notesStore.fetchAllNotes() // 级联删除的笔记需同步出树
  } catch {
    // cancelled or error
  } finally {
    isCreatingFolder.value = false
  }
}
</script>

<style scoped>
.note-tree {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.tree-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 18px 12px;
  border-bottom: 1px solid var(--rh-border-faint);
  transition: border-color var(--rh-duration-normal) var(--rh-transition-normal);
}

.tree-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--rh-text-primary);
}

.category-tree {
  flex: 1;
  overflow-y: auto;
  padding: 12px 10px;
  font-size: 14px;
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 2px 0;
}

.folder-icon {
  color: var(--rh-text-tertiary);
  font-size: 16px;
  flex-shrink: 0;
}

.note-icon {
  font-size: 14px;
  color: var(--rh-text-secondary);
}

.note-label {
  font-size: 13px;
  color: var(--rh-text-secondary);
}

.node-label {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.category-tree :deep(.el-tree-node__content) {
  height: 34px;
  border-radius: 6px;
  transition: var(--rh-transition);
}

.category-tree :deep(.el-tree-node__content:hover) {
  background: var(--rh-bg-hover);
}

.category-tree :deep(.el-tree-node.is-current > .el-tree-node__content) {
  background: var(--rh-primary-subtle);
  color: var(--rh-primary);
}

.category-tree :deep(.el-tree-node.is-current > .el-tree-node__content::before) {
  content: '';
  position: absolute;
  left: 0;
  top: 4px;
  bottom: 4px;
  width: 3px;
  border-radius: 2px;
  background: var(--rh-primary);
}

/* Context Menu */
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
  animation: scaleIn var(--rh-duration-normal) var(--rh-transition-spring) both;
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

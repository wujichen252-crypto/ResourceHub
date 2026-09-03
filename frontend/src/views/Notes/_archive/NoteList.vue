<template>
  <div class="note-list-page">
    <!-- Header -->
    <div class="page-header">
      <div class="page-heading">
        <h1 class="page-title">笔记</h1>
        <p class="page-desc">管理你的知识积累</p>
      </div>
      <el-button type="primary" @click="createNote">
        <el-icon><Plus /></el-icon> 新建笔记
      </el-button>
    </div>

    <el-row :gutter="16" class="page-body">
      <!-- Left: Category Tree -->
      <el-col :xs="24" :sm="6" class="sidebar-col">
        <el-card shadow="never" class="sidebar-card">
          <template #header>
            <span>分类</span>
          </template>
          <el-input
            v-model="searchText"
            placeholder="搜索笔记..."
            :prefix-icon="Search"
            clearable
            class="search-input"
            @input="handleSearch"
          />
          <el-tree
            :data="categoryTree"
            :props="{ children: 'children', label: 'name' }"
            default-expand-all
            highlight-current
            node-key="id"
            :current-node-key="notesStore.selectedCategoryId"
            @node-click="handleCategoryClick"
            class="category-tree"
          />
        </el-card>
      </el-col>

      <!-- Right: Note List -->
      <el-col :xs="24" :sm="18">
        <el-card shadow="never">
          <div v-loading="notesStore.loading" class="note-list">
            <div
              v-for="note in notesStore.notes"
              :key="note.id"
              class="note-card"
              @click="goToNote(note.id)"
            >
              <div class="note-header">
                <h3 class="note-title">
                  <el-tag v-if="note.is_pinned" size="small" type="warning" class="pin-tag">置顶</el-tag>
                  {{ note.title }}
                </h3>
                <div class="note-meta">
                  <span class="note-time">{{ formatDate(note.updated_at) }}</span>
                </div>
              </div>
              <p class="note-preview">{{ note.content_preview || '暂无内容' }}</p>
              <div class="note-footer">
                <el-tag
                  v-if="note.category_name"
                  size="small"
                  type="info"
                >{{ note.category_name }}</el-tag>
                <el-tag
                  v-for="tag in (note.tags || [])"
                  :key="tag"
                  size="small"
                  class="note-tag"
                >{{ tag }}</el-tag>
              </div>
            </div>

            <div v-if="notesStore.notes.length === 0 && !notesStore.loading" class="empty-state">
              <p>还没有笔记</p>
              <el-button type="primary" @click="createNote">创建第一篇笔记</el-button>
            </div>
          </div>

          <div v-if="notesStore.total > notesStore.pageSize" class="pagination-wrapper">
            <el-pagination
              :current-page="notesStore.page"
              :page-size="notesStore.pageSize"
              :total="notesStore.total"
              layout="prev, pager, next"
              @current-change="handlePageChange"
            />
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Search } from '@element-plus/icons-vue'
import { useNotesStore } from '../../stores/notes'
import { useCategoriesStore } from '../../stores/categories'
import type { CategoryTreeNode } from '../../api/categories'

const router = useRouter()
const notesStore = useNotesStore()
const categoriesStore = useCategoriesStore()

const searchText = ref('')
let searchTimer: ReturnType<typeof setTimeout> | null = null

const categoryTree = computed<CategoryTreeNode[]>(() => categoriesStore.noteCategories)

onMounted(() => {
  notesStore.fetchNotes()
  categoriesStore.fetchCategories('note')
})

function handleSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    notesStore.setSearch(searchText.value)
  }, 300)
}

function handleCategoryClick(data: any) {
  notesStore.setCategory(data.id)
}

function handlePageChange(page: number) {
  notesStore.setPage(page)
}

function goToNote(id: number) {
  router.push(`/notes/${id}`)
}

function createNote() {
  router.push('/notes/new')
}

function formatDate(dateStr: string) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.note-list-page {
  padding: 32px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.page-heading {
  flex: 1;
}

.page-title {
  font-size: 26px;
  font-weight: 700;
  color: var(--rh-text-primary);
  margin: 0 0 4px;
}

.page-desc {
  font-size: 14px;
  color: var(--rh-text-tertiary);
  margin: 0;
}

.page-body {
  min-height: 60vh;
}

/* ── Sidebar ── */
.sidebar-col {
  margin-bottom: 16px;
}

.sidebar-card {
  height: 100%;
}

.search-input {
  margin-bottom: 16px;
}

.category-tree {
  font-size: 14px;
}

.category-tree :deep(.el-tree-node__content) {
  height: 36px;
  border-radius: 6px;
  transition: var(--rh-transition);
}

.category-tree :deep(.el-tree-node__content:hover) {
  background: var(--rh-bg-hover);
}

.category-tree :deep(.el-tree-node.is-current > .el-tree-node__content) {
  background: var(--rh-primary-lighter);
  color: var(--rh-primary);
}

/* ── Note Cards (list style) ── */
.note-card {
  padding: 20px;
  border-bottom: 1px solid var(--rh-border-light);
  cursor: pointer;
  transition: var(--rh-transition);
  border-radius: 4px;
}

.note-card:hover {
  background: var(--rh-bg-hover);
  padding-left: 24px;
}

.note-card:last-child {
  border-bottom: none;
}

.note-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
  gap: 12px;
}

.note-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--rh-text-primary);
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  line-height: 1.4;
}

.pin-tag {
  flex-shrink: 0;
}

.note-meta {
  flex-shrink: 0;
  white-space: nowrap;
}

.note-time {
  font-size: 12px;
  color: var(--rh-text-tertiary);
}

.note-preview {
  font-size: 14px;
  color: var(--rh-text-secondary);
  line-height: 1.6;
  margin-bottom: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.note-footer {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.note-tag {
  margin-right: 4px;
}

/* ── Empty State ── */
.empty-state {
  text-align: center;
  padding: 80px 0;
  color: var(--rh-text-tertiary);
}

.empty-state p {
  margin-bottom: 16px;
  font-size: 16px;
}

/* ── Pagination ── */
.pagination-wrapper {
  display: flex;
  justify-content: center;
  padding: 24px 0 8px;
  border-top: 1px solid var(--rh-border-light);
  margin-top: 8px;
}
</style>

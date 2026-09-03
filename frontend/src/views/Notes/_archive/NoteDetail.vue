<template>
  <div class="note-detail-page">
    <div v-if="loading" v-loading="loading" class="loading-container" />

    <template v-if="note && !loading">
      <div class="detail-header">
        <el-button text @click="goBack">
          <el-icon><ArrowLeft /></el-icon> 返回列表
        </el-button>
        <div class="detail-actions">
          <el-button @click="togglePin">
            <el-icon><Top /></el-icon>
            {{ note.is_pinned ? '取消置顶' : '置顶' }}
          </el-button>
          <el-button type="primary" @click="editNote">
            <el-icon><Edit /></el-icon> 编辑
          </el-button>
          <el-button type="danger" @click="deleteNote">
            <el-icon><Delete /></el-icon> 删除
          </el-button>
        </div>
      </div>

      <el-card shadow="never" class="note-content-card">
        <h1 class="note-title">{{ note.title }}</h1>

        <div class="note-metadata">
          <span v-if="note.is_pinned" class="meta-item">
            <el-tag size="small" type="warning">📌 置顶</el-tag>
          </span>
          <span v-if="note.category_name" class="meta-item">{{ note.category_name }}</span>
          <span class="meta-item">创建: {{ formatDate(note.created_at) }}</span>
          <span class="meta-item">更新: {{ formatDate(note.updated_at) }}</span>
        </div>

        <div class="note-tags" v-if="note.tags?.length">
          <el-tag v-for="tag in note.tags" :key="tag" size="small">{{ tag }}</el-tag>
        </div>

        <el-divider />

        <div class="note-content markdown-body" v-html="renderedContent" />
      </el-card>
    </template>

    <div v-if="!note && !loading" class="not-found">
      <p>笔记不存在</p>
      <el-button @click="goBack">返回列表</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Top, Edit, Delete } from '@element-plus/icons-vue'
import MarkdownIt from 'markdown-it'
import { useNotesStore } from '../../stores/notes'

const router = useRouter()
const route = useRoute()
const notesStore = useNotesStore()

const loading = ref(true)
const md = new MarkdownIt({ html: true, linkify: true, typographer: true })

const note = computed(() => notesStore.currentNote)
const renderedContent = computed(() => {
  return note.value?.content ? md.render(note.value.content) : '<p>无内容</p>'
})

async function loadNote(id: number) {
  loading.value = true
  try {
    await notesStore.fetchNote(id)
  } catch {
    notesStore.currentNote = null
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  const id = Number(route.params.id)
  if (id) loadNote(id)
})

watch(() => route.params.id, (newId) => {
  if (newId) loadNote(Number(newId))
})

function goBack() {
  router.push('/notes')
}

async function togglePin() {
  if (!note.value) return
  try {
    await notesStore.togglePin(note.value.id)
    ElMessage.success(note.value.is_pinned ? '已置顶' : '已取消置顶')
  } catch {
    ElMessage.error('操作失败')
  }
}

function editNote() {
  if (!note.value) return
  router.push(`/notes/${note.value.id}/edit`)
}

async function deleteNote() {
  if (!note.value) return
  try {
    await ElMessageBox.confirm('确定要删除这篇笔记吗？此操作不可恢复。', '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await notesStore.deleteNote(note.value.id)
    ElMessage.success('已删除')
    router.push('/notes')
  } catch {
    // cancelled
  }
}

function formatDate(dateStr: string) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('zh-CN')
}
</script>

<style scoped>
.note-detail-page {
  padding: 32px;
  max-width: 860px;
  margin: 0 auto;
}

.loading-container {
  display: flex;
  justify-content: center;
  padding: 100px 0;
}

/* ── Action Bar ── */
.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 8px;
}

.detail-actions {
  display: flex;
  gap: 8px;
}

/* ── Content Card ── */
.note-content-card {
  padding: 8px;
}

.note-title {
  font-size: 30px;
  font-weight: 700;
  color: var(--rh-text-primary);
  margin-bottom: 20px;
  line-height: 1.35;
  letter-spacing: -0.02em;
}

.note-metadata {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.meta-item {
  font-size: 13px;
  color: var(--rh-text-tertiary);
}

.note-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

/* ── Markdown Body ── */
.markdown-body {
  font-size: 15.5px;
  line-height: 1.85;
  color: var(--rh-text-primary);
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  margin-top: 28px;
  margin-bottom: 12px;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.markdown-body :deep(h1) {
  font-size: 24px;
  border-bottom: 1px solid var(--rh-border-light);
  padding-bottom: 8px;
}

.markdown-body :deep(h2) {
  font-size: 20px;
  border-bottom: 1px solid var(--rh-border-light);
  padding-bottom: 6px;
}

.markdown-body :deep(h3) {
  font-size: 17px;
}

.markdown-body :deep(p) {
  margin-bottom: 16px;
}

.markdown-body :deep(code) {
  background: var(--rh-bg-subtle);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 14px;
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  color: var(--rh-primary);
}

.markdown-body :deep(pre) {
  background: #1c1917;
  padding: 20px;
  border-radius: 10px;
  overflow-x: auto;
  margin: 20px 0;
}

.markdown-body :deep(pre code) {
  background: none;
  padding: 0;
  color: #e7e5e4;
  font-size: 13.5px;
  line-height: 1.6;
}

.markdown-body :deep(blockquote) {
  border-left: 3px solid var(--rh-primary);
  padding: 4px 0 4px 20px;
  color: var(--rh-text-secondary);
  margin: 20px 0;
  background: var(--rh-bg-subtle);
  border-radius: 0 8px 8px 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 24px;
  margin-bottom: 16px;
}

.markdown-body :deep(li) {
  margin-bottom: 6px;
}

.markdown-body :deep(img) {
  max-width: 100%;
  border-radius: 8px;
  margin: 16px 0;
}

.markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid var(--rh-border-light);
  margin: 28px 0;
}

.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid var(--rh-border);
  padding: 8px 12px;
  text-align: left;
  font-size: 14px;
}

.markdown-body :deep(th) {
  background: var(--rh-bg-subtle);
  font-weight: 600;
}

/* ── Not Found ── */
.not-found {
  text-align: center;
  padding: 100px 0;
  color: var(--rh-text-tertiary);
}

.not-found p {
  margin-bottom: 16px;
  font-size: 16px;
}
</style>

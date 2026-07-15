<template>
  <div class="dashboard">
    <div class="page-heading">
      <h1 class="page-title">仪表盘</h1>
      <p class="page-desc">欢迎回来，这是你的内容概览</p>
    </div>

    <el-row :gutter="20" class="stat-row">
      <el-col :xs="24" :sm="8">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon stat-icon--note">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.noteCount }}</div>
              <div class="stat-label">笔记总数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="8">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon stat-icon--prompt">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 3 21 3 21 8"/><line x1="4" y1="20" x2="21" y2="3"/><polyline points="21 16 21 21 16 21"/><line x1="15" y1="15" x2="21" y2="21"/><line x1="4" y1="4" x2="9" y2="9"/></svg>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.promptCount }}</div>
              <div class="stat-label">提示词总数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="8">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon stat-icon--fav">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.favoriteCount }}</div>
              <div class="stat-label">收藏提示词</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="content-row">
      <el-col :xs="24" :lg="12">
        <el-card class="content-card">
          <template #header>
            <div class="card-header">
              <span class="card-header-title">最近更新的笔记</span>
              <router-link to="/notes" class="card-more">查看全部 →</router-link>
            </div>
          </template>
          <div v-loading="notesLoading" class="list-container">
            <div v-for="note in recentNotes" :key="note.id" class="list-item">
              <router-link :to="`/notes/${note.id}`" class="list-link">
                {{ note.title }}
              </router-link>
              <span class="list-time">{{ formatTime(note.updated_at) }}</span>
            </div>
            <div v-if="recentNotes.length === 0 && !notesLoading" class="empty-hint">
              暂无笔记
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="12">
        <el-card class="content-card">
          <template #header>
            <div class="card-header">
              <span class="card-header-title">最常使用的提示词</span>
              <router-link to="/prompts" class="card-more">查看全部 →</router-link>
            </div>
          </template>
          <div v-loading="promptsLoading" class="list-container">
            <div v-for="prompt in topPrompts" :key="prompt.id" class="list-item">
              <router-link :to="`/prompts/${prompt.id}`" class="list-link">
                {{ prompt.title }}
              </router-link>
              <span class="list-time">使用 {{ prompt.usage_count }} 次</span>
            </div>
            <div v-if="topPrompts.length === 0 && !promptsLoading" class="empty-hint">
              暂无提示词
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import { useNotesStore } from '../stores/notes'
import { usePromptsStore } from '../stores/prompts'

const notesStore = useNotesStore()
const promptsStore = usePromptsStore()

const stats = reactive({
  noteCount: 0,
  promptCount: 0,
  favoriteCount: 0,
})
const recentNotes = ref<any[]>([])
const topPrompts = ref<any[]>([])
const notesLoading = ref(true)
const promptsLoading = ref(true)

function formatTime(dateStr: string) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${month}/${day}`
}

onMounted(async () => {
  // Fetch recent notes
  try {
    await notesStore.fetchNotes()
    recentNotes.value = notesStore.notes.slice(0, 5)
    stats.noteCount = notesStore.total
  } finally {
    notesLoading.value = false
  }

  // Fetch top prompts
  try {
    await promptsStore.fetchPrompts()
    topPrompts.value = promptsStore.prompts.slice(0, 5)
    stats.promptCount = promptsStore.total
    const favCount = promptsStore.prompts.filter((p: { is_favorite: boolean }) => p.is_favorite).length
    stats.favoriteCount = favCount
  } finally {
    promptsLoading.value = false
  }
})
</script>

<style scoped>
.dashboard {
  padding: 32px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-heading {
  margin-bottom: 28px;
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

/* ── Stat Cards ── */
.stat-row {
  margin-bottom: 28px;
}

.stat-card {
  margin-bottom: 16px;
  cursor: default;
}

.stat-card:hover {
  transform: translateY(-2px);
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 20px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-icon svg {
  width: 22px;
  height: 22px;
}

.stat-icon--note {
  background: #eef2ff;
  color: #4f46e5;
}

.stat-icon--prompt {
  background: #f0fdf4;
  color: #16a34a;
}

.stat-icon--fav {
  background: #fffbeb;
  color: #d97706;
}

.stat-info {
  flex: 1;
  min-width: 0;
}

.stat-value {
  font-size: 30px;
  font-weight: 700;
  color: var(--rh-text-primary);
  line-height: 1.2;
  letter-spacing: -0.02em;
}

.stat-label {
  font-size: 13px;
  color: var(--rh-text-tertiary);
  margin-top: 2px;
}

/* ── Content Cards ── */
.content-row {
  margin-bottom: 24px;
}

.content-card {
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--rh-text-primary);
}

.card-more {
  font-size: 13px;
  color: var(--rh-primary);
  font-weight: 500;
  transition: var(--rh-transition);
}

.card-more:hover {
  color: var(--rh-primary-light);
  gap: 4px;
}

/* ── List Items ── */
.list-container {
  min-height: 60px;
}

.list-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid var(--rh-border-light);
  transition: var(--rh-transition);
}

.list-item:last-child {
  border-bottom: none;
}

.list-item:hover {
  padding-left: 4px;
}

.list-link {
  color: var(--rh-text-primary);
  font-size: 14px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  transition: var(--rh-transition);
}

.list-link:hover {
  color: var(--rh-primary);
}

.list-time {
  font-size: 12px;
  color: var(--rh-text-tertiary);
  white-space: nowrap;
  margin-left: 12px;
  flex-shrink: 0;
}

.empty-hint {
  text-align: center;
  color: var(--rh-text-tertiary);
  padding: 32px 0;
  font-size: 14px;
}
</style>

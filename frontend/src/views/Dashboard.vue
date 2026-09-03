<template>
  <div class="dashboard">
    <div class="page-heading animate-fade-in-up stagger-0">
      <h1 class="page-title">仪表盘</h1>
    </div>

    <!-- Stat Cards with Staggered Entrance -->
    <TransitionGroup name="stagger-list" tag="div" class="stat-row">
      <el-card class="stat-card" :key="'note'">
        <div class="stat-content">
          <div class="stat-icon stat-icon--note">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.noteCount }}</div>
            <div class="stat-label">笔记总数</div>
          </div>
        </div>
      </el-card>

      <el-card class="stat-card" :key="'prompt'">
        <div class="stat-content">
          <div class="stat-icon stat-icon--prompt">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 3 21 3 21 8"/><line x1="4" y1="20" x2="21" y2="3"/><polyline points="21 16 21 21 16 21"/><line x1="15" y1="15" x2="21" y2="21"/><line x1="4" y1="4" x2="9" y2="9"/></svg>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.promptCount }}</div>
            <div class="stat-label">提示词总数</div>
          </div>
        </div>
      </el-card>

      <el-card class="stat-card" :key="'fav'">
        <div class="stat-content">
          <div class="stat-icon stat-icon--fav">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.favoriteCount }}</div>
            <div class="stat-label">收藏提示词</div>
          </div>
        </div>
      </el-card>
    </TransitionGroup>

    <!-- Content Cards -->
    <el-row :gutter="20" class="content-row">
      <el-col :xs="24" :lg="12">
        <Transition name="fade-slide">
          <el-card class="content-card" :key="recentNotes.length">
            <template #header>
              <div class="card-header">
                <span class="card-header-title">最近更新的笔记</span>
                <router-link to="/notes" class="card-more">查看全部 →</router-link>
              </div>
            </template>
            <div v-loading="notesLoading" class="list-container">
              <div v-for="(note, i) in recentNotes" :key="note.id" class="list-item" :class="'stagger-' + Math.min(i, 5)">
                <router-link to="/notes" class="list-link">
                  {{ note.title }}
                </router-link>
                <span class="list-time">{{ formatTime(note.updated_at) }}</span>
              </div>
              <div v-if="recentNotes.length === 0 && !notesLoading" class="empty-hint">
                暂无笔记
              </div>
            </div>
          </el-card>
        </Transition>
      </el-col>

      <el-col :xs="24" :lg="12">
        <Transition name="fade-slide">
          <el-card class="content-card" :key="topPrompts.length">
            <template #header>
              <div class="card-header">
                <span class="card-header-title">最常使用的提示词</span>
                <router-link to="/prompts" class="card-more">查看全部 →</router-link>
              </div>
            </template>
            <div v-loading="promptsLoading" class="list-container">
              <div v-for="(prompt, i) in topPrompts" :key="prompt.id" class="list-item" :class="'stagger-' + Math.min(i, 5)">
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
        </Transition>
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
  margin: 0;
  letter-spacing: -0.02em;
}

/* ── Transition Group Animations ── */

.stagger-list-enter-active {
  animation: fadeInUp var(--rh-duration-slow) var(--rh-transition-normal) both;
}

.stagger-list-enter-active.stagger-0 { animation-delay: 0ms; }
.stagger-list-enter-active.stagger-1 { animation-delay: 80ms; }
.stagger-list-enter-active.stagger-2 { animation-delay: 160ms; }

.stagger-list-leave-active {
  animation: fadeIn var(--rh-duration-fast) var(--rh-transition-fast) both;
}

/* ── Stat Cards ── */

.stat-row {
  margin-bottom: 28px;
}

.stat-card {
  margin-bottom: 16px;
  cursor: default;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--rh-radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: transform var(--rh-duration-normal) var(--rh-transition-spring);
}

.stat-icon svg {
  width: 20px;
  height: 20px;
}

.stat-icon--note {
  background: rgba(124, 58, 237, 0.08);
  color: var(--rh-primary);
}

.stat-icon--prompt {
  background: rgba(5, 150, 105, 0.08);
  color: var(--rh-success);
}

.stat-icon--fav {
  background: rgba(217, 119, 6, 0.08);
  color: var(--rh-warning);
}

.stat-card:hover .stat-icon {
  transform: scale(1.05);
}

.stat-info {
  flex: 1;
  min-width: 0;
}

.stat-value {
  font-size: 28px;
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
  transition: var(--rh-transition-all-normal);
}

.card-more:hover {
  opacity: 0.8;
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
  border-bottom: 1px solid var(--rh-border-faint);
  transition: var(--rh-transition-all-normal);
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
  transition: var(--rh-transition-all-normal);
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

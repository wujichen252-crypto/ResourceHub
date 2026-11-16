<template>
  <div class="rh-page">
    <section class="welcome-row animate-fade-in-up">
      <div><p class="eyebrow">{{ todayLabel }}</p><h1>继续整理你的知识。</h1><p class="welcome-copy">把零散的想法，变成下一次可以直接使用的资源。</p></div>
      <div class="welcome-actions"><el-button @click="router.push('/notes')"><el-icon><EditPen /></el-icon>新建笔记</el-button><el-button type="primary" @click="router.push('/prompts/new')"><el-icon><Plus /></el-icon>新建提示词</el-button></div>
    </section>

    <button class="search-launch animate-fade-in-up stagger-1" @click="router.push({ path: '/prompts', query: { focus: 'search' } })"><el-icon><Search /></el-icon><span>搜索提示词</span><span class="search-hint">前往提示词库</span></button>

    <section class="continue-section animate-fade-in-up stagger-2">
      <div class="section-heading"><div><p class="eyebrow">最近更新</p><h2>最近更新的笔记</h2></div><router-link to="/notes">查看全部 <el-icon><ArrowRight /></el-icon></router-link></div>
      <div class="continue-grid">
        <router-link v-for="note in recentNotes.slice(0, 3)" :key="note.id" to="/notes" class="resource-row">
          <span class="resource-mark note-mark"><el-icon><Document /></el-icon></span><span class="resource-body"><strong>{{ note.title }}</strong><small>笔记 · {{ formatTime(note.updated_at) }}</small></span><el-icon class="row-arrow"><ArrowRight /></el-icon>
        </router-link>
        <div v-if="!notesLoading && recentNotes.length === 0" class="empty-row"><el-icon><Document /></el-icon><span>还没有笔记，先写下第一个想法。</span><router-link to="/notes">开始记录</router-link></div>
      </div>
    </section>

    <section class="content-grid animate-fade-in-up stagger-3">
      <div class="panel prompt-panel"><div class="section-heading"><div><p class="eyebrow ai-label">AI 资源</p><h2>常用提示词</h2></div><router-link to="/prompts">进入库 <el-icon><ArrowRight /></el-icon></router-link></div><div class="prompt-list">
        <router-link v-for="(prompt, index) in topPrompts" :key="prompt.id" :to="`/prompts/${prompt.id}`" class="prompt-row"><span class="prompt-number">{{ String(index + 1).padStart(2, '0') }}</span><span class="resource-body"><strong>{{ prompt.title }}</strong><small>{{ prompt.category_name || '未分类' }} · 使用 {{ prompt.usage_count }} 次</small></span><el-icon class="row-arrow"><ArrowRight /></el-icon></router-link>
        <div v-if="!promptsLoading && topPrompts.length === 0" class="empty-row"><el-icon><MagicStick /></el-icon><span>创建一个可复用的提示词模板。</span><router-link to="/prompts/new">开始创建</router-link></div>
      </div></div>
      <div class="overview-panel"><p class="eyebrow">资源概览</p><h2>你的工作台</h2><div class="metric-list"><div><strong>{{ stats.noteCount }}</strong><span>篇笔记</span></div><div><strong>{{ stats.promptCount }}</strong><span>个提示词</span></div><div><strong>{{ stats.favoriteCount }}</strong><span>个收藏</span></div></div><div class="ai-callout"><span class="ai-symbol">✦</span><div><strong>让资源持续产生价值</strong><p>把一次性的好想法，保存成下一次可以直接复用的模板。</p></div></div></div>
    </section>

    <!-- 每日回顾：往年今日 / 本周沉淀 / 连续记录 / 昨日遗留任务 -->
    <section v-if="dailyReview" class="review-section animate-fade-in-up stagger-4">
      <div class="section-heading"><div><p class="eyebrow">每日回顾</p><h2>{{ reviewHeading }}</h2></div><router-link to="/notes">去笔记库 <el-icon><ArrowRight /></el-icon></router-link></div>
      <div class="review-grid">
        <div class="review-metrics">
          <button type="button" class="review-metric" :disabled="!dailyReview.this_week" @click="router.push('/notes')">
            <strong>{{ dailyReview.this_week }}</strong><span>本周沉淀</span>
          </button>
          <div class="review-metric">
            <strong>{{ dailyReview.streak }}</strong><span>连续记录 · 天</span>
          </div>
          <div class="review-metric">
            <strong>{{ dailyReview.on_this_day_total }}</strong><span>往年今日</span>
          </div>
        </div>
        <div class="review-lists">
          <div v-if="dailyReview.pending_tasks.length" class="review-block">
            <p class="review-block-title">昨日遗留任务</p>
            <button
              v-for="(task, index) in dailyReview.pending_tasks"
              :key="`${task.note_id}-${index}`"
              type="button"
              class="review-task-row"
              @click="router.push(`/notes?note=${task.note_id}`)"
            >
              <span class="task-checkbox" aria-hidden="true"></span>
              <span class="review-task-text">{{ task.task }}</span>
              <span class="review-task-from">来自「{{ task.note_title }}」</span>
            </button>
          </div>
          <div v-if="dailyReview.on_this_day.length" class="review-block">
            <p class="review-block-title">那年今天</p>
            <button
              v-for="item in dailyReview.on_this_day"
              :key="item.id"
              type="button"
              class="review-task-row"
              @click="router.push(`/notes?note=${item.id}`)"
            >
              <span class="review-year">{{ item.years_ago }} 年前</span>
              <span class="review-task-text">{{ item.title }}</span>
            </button>
          </div>
          <div v-if="!dailyReview.pending_tasks.length && !dailyReview.on_this_day.length" class="empty-row">
            <el-icon><Document /></el-icon><span>继续记录，未来的某一天会在这里与过去的自己重逢。</span>
          </div>
        </div>
      </div>
    </section>

    <section v-if="unreadProactive.length" class="proactive-section animate-fade-in-up">
      <div class="section-heading">
        <div><p class="eyebrow ai-label">AI 主动提醒</p><h2>你的知识分身有话要说</h2></div>
        <router-link to="/ai">进入工作台 <el-icon><ArrowRight /></el-icon></router-link>
      </div>
      <div class="proactive-list">
        <router-link v-for="message in unreadProactive.slice(0, 2)" :key="message.id" to="/ai" class="proactive-row">
          <span class="proactive-mark"><el-icon><Bell /></el-icon></span>
          <span class="resource-body"><strong>{{ message.title }}</strong><small>{{ message.content }}</small></span>
          <el-icon class="row-arrow"><ArrowRight /></el-icon>
        </router-link>
      </div>
    </section>

    <section v-if="overview" class="viz-grid animate-fade-in-up stagger-4">
      <TagCloud :items="overview.tag_cloud" />
      <CreationTrend :points="overview.creation_trend" />
      <CategoryDonut :items="overview.category_distribution" />
      <UsageHeatmap :points="overview.usage_heatmap" />
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, Bell, Document, EditPen, MagicStick, Plus, Search } from '@element-plus/icons-vue'
import { useNotesStore } from '../stores/notes'
import { usePromptsStore } from '../stores/prompts'
import { formatRelative } from '../utils/format'
import { statsApi, type StatsOverview, type DailyReview } from '../api/stats'
import { useAgentIdentityStore } from '../stores/agentIdentity'
import TagCloud from '../components/dashboard/TagCloud.vue'
import CreationTrend from '../components/dashboard/CreationTrend.vue'
import CategoryDonut from '../components/dashboard/CategoryDonut.vue'
import UsageHeatmap from '../components/dashboard/UsageHeatmap.vue'

const router = useRouter(); const notesStore = useNotesStore(); const promptsStore = usePromptsStore(); const identity = useAgentIdentityStore()
const stats = reactive({ noteCount: 0, promptCount: 0, favoriteCount: 0 }); const recentNotes = ref<any[]>([]); const topPrompts = ref<any[]>([]); const notesLoading = ref(true); const promptsLoading = ref(true)
const overview = ref<StatsOverview | null>(null)
const dailyReview = ref<DailyReview | null>(null)
const unreadProactive = computed(() => identity.proactive.filter((item) => item.status === 'unread'))
const todayLabel = computed(() => { const d = new Date(); return `${d.getFullYear()} / ${String(d.getMonth() + 1).padStart(2, '0')} / ${String(d.getDate()).padStart(2, '0')}` })
const reviewHeading = computed(() => {
  const streak = dailyReview.value?.streak ?? 0
  if (streak >= 2) return `已连续记录 ${streak} 天`
  if (dailyReview.value?.this_week) return '本周也在持续沉淀'
  return '看看过去的自己'
})
function formatTime(value: string) { return formatRelative(value) || '最近更新' }
onMounted(async () => {
  // 图表统计与主内容并行请求，统计失败不阻塞主内容
  const statsPromise = statsApi.overview().then((d) => { overview.value = d }).catch(() => { /* 统计失败不阻塞主内容 */ })
  const reviewPromise = statsApi.dailyReview().then((d) => { dailyReview.value = d }).catch(() => { /* 回顾失败不阻塞主内容 */ })
  const proactivePromise = identity.loadProactive().catch(() => { /* 主动消息失败不阻塞主内容 */ })
  try {
    await notesStore.fetchNotes()
    recentNotes.value = notesStore.notes
    stats.noteCount = notesStore.total
  } finally { notesLoading.value = false }
  try {
    await promptsStore.fetchPrompts()
    // 「常用提示词」按使用次数排序，而非接口默认顺序
    topPrompts.value = [...promptsStore.prompts].sort((a, b) => (b.usage_count ?? 0) - (a.usage_count ?? 0)).slice(0, 4)
    stats.promptCount = promptsStore.total
    // 收藏数取服务端全量 total，避免只统计当前分页导致数字偏小
    await promptsStore.fetchFavoriteTotal()
    stats.favoriteCount = promptsStore.favoriteTotal
  } finally { promptsLoading.value = false }
  await Promise.all([statsPromise, reviewPromise, proactivePromise])
})
</script>

<style scoped>
.welcome-row { display: flex; align-items: flex-end; justify-content: space-between; gap: 28px; margin-bottom: 32px; }.eyebrow { margin-bottom: 7px; color: var(--rh-text-tertiary); font-size: 11px; font-weight: 700; letter-spacing: .04em; }.welcome-row h1 { font-family: var(--rh-font-display); font-size: clamp(30px, 4vw, 48px); line-height: 1.12; font-weight: 500; letter-spacing: 0; }.welcome-copy { margin-top: 12px; color: var(--rh-text-secondary); font-size: 15px; }.welcome-actions { display: flex; flex-wrap: wrap; gap: 8px; }
.search-launch { display: flex; align-items: center; width: 100%; height: 52px; padding: 0 16px; border: 1px solid var(--rh-border); border-radius: var(--rh-radius-sm); background: var(--rh-bg-card); color: var(--rh-text-secondary); text-align: left; cursor: pointer; box-shadow: var(--rh-shadow-sm); transition: var(--rh-transition-all-normal); }.search-launch:hover { border-color: var(--rh-primary); box-shadow: var(--rh-shadow-md); }.search-launch :deep(.el-icon) { margin-right: 11px; color: var(--rh-primary); font-size: 18px; }.search-hint { margin-left: auto; color: var(--rh-text-tertiary); font-size: 12px; }
.continue-section { margin-top: 54px; }.section-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; margin-bottom: 16px; }.section-heading h2, .overview-panel h2 { font-family: var(--rh-font-display); font-size: 23px; font-weight: 500; }.section-heading a { display: inline-flex; align-items: center; gap: 4px; color: var(--rh-text-secondary); font-size: 13px; font-weight: 600; }.section-heading a:hover { color: var(--rh-primary); }.section-heading a :deep(.el-icon) { font-size: 14px; }.continue-grid { border-top: 1px solid var(--rh-border); }.resource-row, .prompt-row { position: relative; display: flex; align-items: center; gap: 13px; min-height: 70px; padding: 10px 0; border-bottom: 1px solid var(--rh-border-faint); color: var(--rh-text-primary); transition: var(--rh-transition-all-normal); }.resource-row::before, .prompt-row::before { position: absolute; left: 0; top: 10px; bottom: 10px; width: 2px; border-radius: 1px; background: transparent; content: ''; transition: var(--rh-transition-all-fast); }.resource-row:hover, .prompt-row:hover { background: var(--rh-bg-hover); }.resource-row:hover::before, .prompt-row:hover::before { background: var(--rh-primary); }.resource-mark { display: grid; place-items: center; width: 35px; height: 35px; border-radius: 50%; flex: 0 0 auto; }.note-mark { background: var(--rh-primary-subtle); color: var(--rh-primary); }.resource-body { display: block; min-width: 0; flex: 1; }.resource-body strong, .resource-body small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.resource-body strong { font-size: 14px; font-weight: 700; }.resource-body small { margin-top: 3px; color: var(--rh-text-tertiary); font-size: 12px; }.row-arrow { color: var(--rh-text-tertiary); }.empty-row { display: flex; align-items: center; gap: 9px; min-height: 84px; color: var(--rh-text-tertiary); font-size: 13px; }.empty-row a { margin-left: auto; font-weight: 700; }
.content-grid { display: grid; grid-template-columns: minmax(0, 1.55fr) minmax(260px, .85fr); gap: 20px; margin-top: 52px; }
.proactive-section { margin-top: 52px; }.proactive-list { border-top: 1px solid var(--rh-border); }.proactive-row { display: flex; align-items: center; gap: 13px; min-height: 74px; padding: 12px 0; border-bottom: 1px solid var(--rh-border-faint); color: var(--rh-text-primary); transition: var(--rh-transition-all-normal); }.proactive-row:hover { background: var(--rh-bg-hover); }.proactive-mark { display: grid; place-items: center; width: 35px; height: 35px; flex: 0 0 auto; border-radius: 50%; background: var(--rh-bg-active); color: var(--rh-ai-strong); }.proactive-row .resource-body small { display: -webkit-box; white-space: normal; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
/* ── 每日回顾 ── */
.review-section { margin-top: 52px; }
.review-grid { display: grid; grid-template-columns: minmax(220px, 0.6fr) minmax(0, 1.4fr); gap: 20px; border-top: 1px solid var(--rh-border); padding-top: 20px; }
.review-metrics { display: flex; flex-direction: column; gap: 12px; }
.review-metric { display: flex; align-items: baseline; gap: 10px; padding: 12px 16px; border: 1px solid var(--rh-border-faint); border-radius: var(--rh-radius-sm); background: var(--rh-bg-card); cursor: default; transition: var(--rh-transition-all-normal); }
.review-metric:disabled { cursor: default; opacity: 0.65; }
.review-metric:not(:disabled):hover { border-color: var(--rh-primary-muted); background: var(--rh-bg-hover); }
.review-metric strong { font-family: var(--rh-font-display); font-size: 24px; font-weight: 500; color: var(--rh-primary); }
.review-metric span { color: var(--rh-text-tertiary); font-size: 12px; }
.review-lists { display: flex; flex-direction: column; gap: 18px; min-width: 0; }
.review-block-title { color: var(--rh-text-tertiary); font-size: 12px; font-weight: 700; letter-spacing: 0.04em; margin-bottom: 8px; }
.review-task-row { display: flex; align-items: center; gap: 10px; width: 100%; min-height: 40px; padding: 6px 10px; border: 1px solid transparent; border-radius: var(--rh-radius-xs); background: transparent; color: var(--rh-text-primary); font-size: 13px; text-align: left; cursor: pointer; transition: var(--rh-transition-all-normal); }
.review-task-row:hover { background: var(--rh-bg-hover); color: var(--rh-primary); }
.task-checkbox { flex-shrink: 0; width: 14px; height: 14px; border: 1.5px solid var(--rh-border-strong); border-radius: var(--rh-radius-xs); }
.review-year { flex-shrink: 0; padding: 2px 8px; border-radius: var(--rh-radius-xs); background: var(--rh-primary-subtle); color: var(--rh-primary); font-size: 12px; }
.review-task-text { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.review-task-from { flex-shrink: 0; max-width: 40%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--rh-text-tertiary); font-size: 12px; }
@media (max-width: 800px) { .review-grid { grid-template-columns: 1fr; } .review-metrics { flex-direction: row; } .review-metric { flex: 1; } }
.viz-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; margin-top: 52px; }.panel, .overview-panel { border: 1px solid var(--rh-border); background: var(--rh-bg-card); }.panel { padding: 22px 24px; }.prompt-panel .section-heading { margin-bottom: 8px; }.prompt-list { border-top: 1px solid var(--rh-border); }.prompt-row { min-height: 64px; }.prompt-number { width: 25px; color: var(--rh-text-tertiary); font-family: var(--rh-font-sans); font-size: 12px; font-variant-numeric: tabular-nums; }.ai-label { color: var(--rh-ai-strong); }.overview-panel { position: relative; overflow: hidden; padding: 24px; background: var(--rh-text-primary); color: var(--rh-bg-card); }.overview-panel::after { position: absolute; top: -30px; right: -20px; width: 140px; height: 140px; border: 1px solid rgba(183,216,75,.4); border-radius: 50%; content: ''; }.overview-panel .eyebrow { color: var(--rh-ai); }.metric-list { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 32px 0 28px; }.metric-list div { padding-right: 10px; border-right: 1px solid var(--rh-on-inverse-line); }.metric-list div:last-child { border-right: 0; }.metric-list strong, .metric-list span { display: block; }.metric-list strong { font-family: var(--rh-font-display); font-size: 27px; font-weight: 500; }.metric-list span { margin-top: 4px; color: var(--rh-on-inverse-muted); font-size: 11px; }.ai-callout { display: flex; gap: 12px; padding-top: 18px; border-top: 1px solid var(--rh-on-inverse-line); }.ai-symbol { color: var(--rh-ai); font-size: 19px; }.ai-callout strong { font-size: 13px; }.ai-callout p { margin-top: 5px; color: var(--rh-on-inverse-muted); font-size: 12px; line-height: 1.6; }
@media (max-width: 800px) { .welcome-row { display: block; }.welcome-actions { margin-top: 22px; }.content-grid { grid-template-columns: 1fr; }.viz-grid { grid-template-columns: 1fr; }.continue-section { margin-top: 40px; } }
@media (max-width: 480px) { .welcome-row h1 { font-size: 32px; }.welcome-actions .el-button { flex: 1; }.search-hint { display: none; }.panel { padding: 18px; } }
</style>

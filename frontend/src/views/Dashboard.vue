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
import { ArrowRight, Document, EditPen, MagicStick, Plus, Search } from '@element-plus/icons-vue'
import { useNotesStore } from '../stores/notes'
import { usePromptsStore } from '../stores/prompts'
import { formatRelative } from '../utils/format'
import { statsApi, type StatsOverview } from '../api/stats'
import TagCloud from '../components/dashboard/TagCloud.vue'
import CreationTrend from '../components/dashboard/CreationTrend.vue'
import CategoryDonut from '../components/dashboard/CategoryDonut.vue'
import UsageHeatmap from '../components/dashboard/UsageHeatmap.vue'

const router = useRouter(); const notesStore = useNotesStore(); const promptsStore = usePromptsStore()
const stats = reactive({ noteCount: 0, promptCount: 0, favoriteCount: 0 }); const recentNotes = ref<any[]>([]); const topPrompts = ref<any[]>([]); const notesLoading = ref(true); const promptsLoading = ref(true)
const overview = ref<StatsOverview | null>(null)
const todayLabel = computed(() => { const d = new Date(); return `${d.getFullYear()} / ${String(d.getMonth() + 1).padStart(2, '0')} / ${String(d.getDate()).padStart(2, '0')}` })
function formatTime(value: string) { return formatRelative(value) || '最近更新' }
onMounted(async () => {
  // 图表统计与主内容并行请求，统计失败不阻塞主内容
  const statsPromise = statsApi.overview().then((d) => { overview.value = d }).catch(() => { /* 统计失败不阻塞主内容 */ })
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
  await statsPromise
})
</script>

<style scoped>
.welcome-row { display: flex; align-items: flex-end; justify-content: space-between; gap: 28px; margin-bottom: 32px; }.eyebrow { margin-bottom: 7px; color: var(--rh-text-tertiary); font-size: 11px; font-weight: 700; letter-spacing: .04em; }.welcome-row h1 { font-family: var(--rh-font-display); font-size: clamp(30px, 4vw, 48px); line-height: 1.12; font-weight: 500; letter-spacing: 0; }.welcome-copy { margin-top: 12px; color: var(--rh-text-secondary); font-size: 15px; }.welcome-actions { display: flex; flex-wrap: wrap; gap: 8px; }
.search-launch { display: flex; align-items: center; width: 100%; height: 52px; padding: 0 16px; border: 1px solid var(--rh-border); border-radius: var(--rh-radius-sm); background: var(--rh-bg-card); color: var(--rh-text-secondary); text-align: left; cursor: pointer; box-shadow: var(--rh-shadow-sm); transition: var(--rh-transition-all-normal); }.search-launch:hover { border-color: var(--rh-primary); box-shadow: var(--rh-shadow-md); }.search-launch :deep(.el-icon) { margin-right: 11px; color: var(--rh-primary); font-size: 18px; }.search-hint { margin-left: auto; color: var(--rh-text-tertiary); font-size: 12px; }
.continue-section { margin-top: 54px; }.section-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; margin-bottom: 16px; }.section-heading h2, .overview-panel h2 { font-family: var(--rh-font-display); font-size: 23px; font-weight: 500; }.section-heading a { display: inline-flex; align-items: center; gap: 4px; color: var(--rh-text-secondary); font-size: 13px; font-weight: 600; }.section-heading a:hover { color: var(--rh-primary); }.section-heading a :deep(.el-icon) { font-size: 14px; }.continue-grid { border-top: 1px solid var(--rh-border); }.resource-row, .prompt-row { position: relative; display: flex; align-items: center; gap: 13px; min-height: 70px; padding: 10px 0; border-bottom: 1px solid var(--rh-border-faint); color: var(--rh-text-primary); transition: var(--rh-transition-all-normal); }.resource-row::before, .prompt-row::before { position: absolute; left: 0; top: 10px; bottom: 10px; width: 2px; border-radius: 1px; background: transparent; content: ''; transition: var(--rh-transition-all-fast); }.resource-row:hover, .prompt-row:hover { background: var(--rh-bg-hover); }.resource-row:hover::before, .prompt-row:hover::before { background: var(--rh-primary); }.resource-mark { display: grid; place-items: center; width: 35px; height: 35px; border-radius: 50%; flex: 0 0 auto; }.note-mark { background: var(--rh-primary-subtle); color: var(--rh-primary); }.resource-body { display: block; min-width: 0; flex: 1; }.resource-body strong, .resource-body small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.resource-body strong { font-size: 14px; font-weight: 700; }.resource-body small { margin-top: 3px; color: var(--rh-text-tertiary); font-size: 12px; }.row-arrow { color: var(--rh-text-tertiary); }.empty-row { display: flex; align-items: center; gap: 9px; min-height: 84px; color: var(--rh-text-tertiary); font-size: 13px; }.empty-row a { margin-left: auto; font-weight: 700; }
.content-grid { display: grid; grid-template-columns: minmax(0, 1.55fr) minmax(260px, .85fr); gap: 20px; margin-top: 52px; }
.viz-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; margin-top: 52px; }.panel, .overview-panel { border: 1px solid var(--rh-border); background: var(--rh-bg-card); }.panel { padding: 22px 24px; }.prompt-panel .section-heading { margin-bottom: 8px; }.prompt-list { border-top: 1px solid var(--rh-border); }.prompt-row { min-height: 64px; }.prompt-number { width: 25px; color: var(--rh-text-tertiary); font-family: var(--rh-font-sans); font-size: 12px; font-variant-numeric: tabular-nums; }.ai-label { color: var(--rh-ai-strong); }.overview-panel { position: relative; overflow: hidden; padding: 24px; background: var(--rh-text-primary); color: var(--rh-bg-card); }.overview-panel::after { position: absolute; top: -30px; right: -20px; width: 140px; height: 140px; border: 1px solid rgba(183,216,75,.4); border-radius: 50%; content: ''; }.overview-panel .eyebrow { color: var(--rh-ai); }.metric-list { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 32px 0 28px; }.metric-list div { padding-right: 10px; border-right: 1px solid var(--rh-on-inverse-line); }.metric-list div:last-child { border-right: 0; }.metric-list strong, .metric-list span { display: block; }.metric-list strong { font-family: var(--rh-font-display); font-size: 27px; font-weight: 500; }.metric-list span { margin-top: 4px; color: var(--rh-on-inverse-muted); font-size: 11px; }.ai-callout { display: flex; gap: 12px; padding-top: 18px; border-top: 1px solid var(--rh-on-inverse-line); }.ai-symbol { color: var(--rh-ai); font-size: 19px; }.ai-callout strong { font-size: 13px; }.ai-callout p { margin-top: 5px; color: var(--rh-on-inverse-muted); font-size: 12px; line-height: 1.6; }
@media (max-width: 800px) { .welcome-row { display: block; }.welcome-actions { margin-top: 22px; }.content-grid { grid-template-columns: 1fr; }.viz-grid { grid-template-columns: 1fr; }.continue-section { margin-top: 40px; } }
@media (max-width: 480px) { .welcome-row h1 { font-size: 32px; }.welcome-actions .el-button { flex: 1; }.search-hint { display: none; }.panel { padding: 18px; } }
</style>

<template>
  <div class="rh-page">
    <header class="roi-head">
      <div>
        <p class="eyebrow">知识资产 ROI</p>
        <h1>AI 成本与效果看板</h1>
        <p class="sub">量化每一次 AI 投入，看清哪些知识资产真正在产生价值。</p>
      </div>
      <el-radio-group :model-value="days" @update:model-value="changeDays">
        <el-radio-button v-for="d in [7, 30, 90]" :key="d" :value="d">{{ d }} 天</el-radio-button>
      </el-radio-group>
    </header>

    <LoadingState v-if="loading" variant="chart" :count="4" label="看板加载中" />

    <EmptyState
      v-else-if="summary && summary.total_calls === 0"
      :icon="DataAnalysis"
      title="还没有 AI 使用记录"
      description="先去 AI 工作台体验一次对话问答，或为提示词跑一轮评测，这里就会长出你的投入产出数据。"
    >
      <el-button type="primary" @click="$router.push('/ai')">去体验 AI 工作台</el-button>
    </EmptyState>

    <template v-else-if="summary">
      <!-- 指标条 -->
      <section class="metric-strip">
        <div class="metric"><small>折算成本</small><strong>{{ fmtMoney(summary.cost_total) }}</strong><span v-if="summary.unpriced_tokens > 0">另有 {{ fmtTokens(summary.unpriced_tokens) }} token 未计价</span></div>
        <div class="metric"><small>总 Token</small><strong>{{ fmtTokens(summary.total_tokens) }}</strong><span>{{ summary.total_calls }} 次调用</span></div>
        <div class="metric"><small>成功率</small><strong>{{ (summary.success_rate * 100).toFixed(1) }}%</strong><span>平均 {{ summary.avg_latency_ms }} ms</span></div>
        <div class="metric"><small>今日配额</small><strong>{{ quotaPercent }}%</strong><span>{{ fmtTokens(summary.quota_used_today) }} / {{ fmtTokens(summary.quota_limit) }}</span></div>
      </section>

      <section class="roi-grid">
        <!-- 成本趋势 -->
        <VizCard class="span-2" eyebrow="成本水位" title="调用趋势" hint="逐日 token 用量（按场景堆叠）与折算金额" empty="暂无趋势数据" :has-data="trendPoints.length > 0">
          <div ref="trendEl" class="viz-chart"></div>
          <template #sr-table>
            <table class="viz-sr-table" aria-hidden="false" aria-label="AI 调用趋势数据摘要">
              <caption class="sr-only">逐日 AI 调用次数、token 与折算金额</caption>
              <thead><tr><th scope="col">日期</th><th scope="col">调用</th><th scope="col">Token</th><th scope="col">金额（元）</th></tr></thead>
              <tbody><tr v-for="p in trendPoints" :key="p.date"><td>{{ p.date }}</td><td>{{ p.calls }}</td><td>{{ p.tokens }}</td><td>{{ p.cost }}</td></tr></tbody>
            </table>
          </template>
        </VizCard>

        <!-- 场景成本占比 -->
        <VizCard eyebrow="成本结构" title="场景成本占比" hint="按调用场景折算的金额分布" empty="暂无成本数据（所用模型未配置单价）" :has-data="summary.by_scene.some(s => s.cost > 0)">
          <div ref="sceneEl" class="viz-chart"></div>
          <template #sr-table>
            <table class="viz-sr-table" aria-hidden="false" aria-label="场景成本占比数据摘要">
              <caption class="sr-only">各调用场景的 token 与折算金额</caption>
              <thead><tr><th scope="col">场景</th><th scope="col">Token</th><th scope="col">金额（元）</th></tr></thead>
              <tbody><tr v-for="s in summary.by_scene" :key="s.scene"><td>{{ sceneLabels[s.scene] || s.scene }}</td><td>{{ s.tokens }}</td><td>{{ s.cost }}</td></tr></tbody>
            </table>
          </template>
        </VizCard>

        <!-- 场景四象限 -->
        <VizCard eyebrow="投入产出" title="场景四象限" hint="X 轴调用次数 · Y 轴折算成本；左下明星区，右上待优化区" empty="暂无场景数据" :has-data="scenePoints.length > 0">
          <div ref="quadrantEl" class="viz-chart"></div>
          <template #sr-table>
            <table class="viz-sr-table" aria-hidden="false" aria-label="场景四象限数据摘要">
              <caption class="sr-only">各场景调用次数与折算成本</caption>
              <thead><tr><th scope="col">场景</th><th scope="col">调用次数</th><th scope="col">金额（元）</th></tr></thead>
              <tbody><tr v-for="s in scenePoints" :key="s.scene"><td>{{ sceneLabels[s.scene] || s.scene }}</td><td>{{ s.calls }}</td><td>{{ s.cost }}</td></tr></tbody>
            </table>
          </template>
        </VizCard>

        <!-- 知识资产健康度 -->
        <VizCard class="span-2" eyebrow="知识资产" title="笔记健康度" hint="高产出值得维护；沉睡资产考虑归档或补充标签" empty="暂无笔记资产数据" :has-data="noteItems.length > 0">
          <el-table :data="noteItems" size="small" class="roi-table">
            <el-table-column prop="title" label="笔记" min-width="180" show-overflow-tooltip />
            <el-table-column label="健康度" width="110">
              <template #default="{ row }"><el-tag :type="gradeTag(row.grade as NoteGrade)" size="small" effect="plain">{{ gradeLabels[row.grade as NoteGrade] }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="citations" label="AI 引用" width="90" align="right" />
            <el-table-column label="索引成本" width="110" align="right">
              <template #default="{ row }">{{ row.index_cost === null ? '未计价' : fmtMoney(row.index_cost) }}</template>
            </el-table-column>
            <el-table-column prop="roi_score" label="ROI 分" width="90" align="right" />
          </el-table>
        </VizCard>

        <!-- 提示词性价比 -->
        <VizCard class="span-2" eyebrow="提示词资产" title="性价比排行" hint="使用次数 × 质量分 ÷ 优化投入；点击进入提示词详情" empty="暂无提示词资产数据" :has-data="promptItems.length > 0">
          <div ref="promptEl" class="viz-chart viz-chart--wide"></div>
          <template #sr-table>
            <table class="viz-sr-table" aria-hidden="false" aria-label="提示词性价比数据摘要">
              <caption class="sr-only">提示词使用次数、质量分与 ROI 评分</caption>
              <thead><tr><th scope="col">提示词</th><th scope="col">使用次数</th><th scope="col">质量分</th><th scope="col">ROI 分</th></tr></thead>
              <tbody><tr v-for="p in promptItems" :key="p.prompt_id"><td>{{ p.title }}</td><td>{{ p.usage_count }}</td><td>{{ p.quality_score ?? '未评测' }}</td><td>{{ p.roi_score }}</td></tr></tbody>
            </table>
          </template>
        </VizCard>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
/** AI 成本与效果看板（知识资产 ROI）：成本水位 → 场景结构 → 笔记/提示词投入产出 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { DataAnalysis } from '@element-plus/icons-vue'
import { baseChartOption, themeVar, useChart } from '../composables/useChart'
import VizCard from '../components/dashboard/VizCard.vue'
import LoadingState from '../components/common/LoadingState.vue'
import EmptyState from '../components/common/EmptyState.vue'
import {
  gradeLabels,
  roiApi,
  sceneLabels,
  type NoteGrade,
  type NoteRoiItem,
  type PromptRoiItem,
  type RoiSummary,
  type RoiTrendPoint,
  type SceneQuadrantPoint,
} from '../api/roi'

const router = useRouter()
const days = ref(30)
const loading = ref(true)
const summary = ref<RoiSummary | null>(null)
const trendPoints = ref<RoiTrendPoint[]>([])
const noteItems = ref<NoteRoiItem[]>([])
const promptItems = ref<PromptRoiItem[]>([])
const scenePoints = ref<SceneQuadrantPoint[]>([])

const primary = () => themeVar('--rh-primary', '#b03c22')
const palette = () => [
  themeVar('--rh-primary', '#b03c22'),
  themeVar('--rh-ai-strong', '#5f7410'),
  themeVar('--rh-success', '#3f8f6b'),
  themeVar('--rh-warning', '#9a6a1c'),
  themeVar('--rh-info', '#6a7268'),
  themeVar('--rh-primary-active', '#7f2714'),
]

// ── 格式化 ──────────────────────────────────────
function fmtMoney(v: number): string {
  if (v > 0 && v < 0.01) return '<¥0.01'
  return `¥${v.toFixed(2)}`
}
function fmtTokens(v: number): string {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}m`
  if (v >= 1000) return `${(v / 1000).toFixed(1)}k`
  return String(v)
}
const quotaPercent = computed(() => {
  if (!summary.value || summary.value.quota_limit <= 0) return '—'
  const pct = (summary.value.quota_used_today / summary.value.quota_limit) * 100
  if (pct > 0 && pct < 1) return '<1'
  return String(Math.min(100, Math.round(pct)))
})
function gradeTag(grade: NoteGrade): 'success' | 'primary' | 'warning' | 'danger' | 'info' {
  switch (grade) {
    case 'high_yield': return 'success'
    case 'normal': return 'primary'
    case 'sleeping': return 'info'
    case 'cost_heavy': return 'danger'
    default: return 'info'
  }
}

// ── 图表 ────────────────────────────────────────
const trendEl = ref<HTMLElement | null>(null)
useChart(trendEl, {
  watchSource: trendPoints,
  buildOption: () => ({
    ...baseChartOption(),
    grid: { left: 48, right: 52, top: 34, bottom: 26 },
    legend: { top: 0, right: 0, itemWidth: 14, textStyle: { color: themeVar('--rh-text-secondary'), fontSize: 12 } },
    tooltip: { ...baseChartOption().tooltip, trigger: 'axis' },
    xAxis: {
      type: 'category', boundaryGap: false,
      data: trendPoints.value.map((p) => p.date.slice(5)),
      axisLine: { lineStyle: { color: themeVar('--rh-border') } },
      axisTick: { show: false },
      axisLabel: { color: themeVar('--rh-text-secondary'), fontSize: 12 },
    },
    yAxis: [
      { type: 'value', splitLine: { lineStyle: { color: themeVar('--rh-border-faint') } }, axisLabel: { color: themeVar('--rh-text-secondary'), fontSize: 12 } },
      { type: 'value', splitLine: { show: false }, axisLabel: { color: themeVar('--rh-text-secondary'), fontSize: 12, formatter: (v: number) => `¥${v === 0 ? '0' : v < 0.1 ? v.toFixed(4) : v.toFixed(2)}` } },
    ],
    series: [
      ...sceneKeys.value.map((scene, i) => ({
        name: sceneLabels[scene] || scene,
        type: 'line', stack: 'tokens', smooth: true, symbol: 'none',
        lineStyle: { width: 1 },
        areaStyle: { opacity: 0.18 },
        color: palette()[i % palette().length],
        data: trendPoints.value.map((p) => p.scenes[scene] || 0),
      })),
      {
        name: '折算金额', type: 'line', yAxisIndex: 1, smooth: true, symbol: 'none',
        lineStyle: { color: primary(), width: 2, type: 'dashed' },
        data: trendPoints.value.map((p) => p.cost),
      },
    ],
  }),
})

const sceneKeys = computed(() => {
  const keys = new Set<string>()
  trendPoints.value.forEach((p) => Object.keys(p.scenes).forEach((k) => keys.add(k)))
  return [...keys]
})

const sceneEl = ref<HTMLElement | null>(null)
useChart(sceneEl, {
  watchSource: computed(() => summary.value?.by_scene),
  buildOption: () => ({
    ...baseChartOption(),
    tooltip: { ...baseChartOption().tooltip, trigger: 'item', valueFormatter: (v: number) => `¥${v.toFixed(4)}` },
    series: [{
      type: 'pie', radius: ['52%', '76%'], center: ['50%', '52%'],
      label: { color: themeVar('--rh-text-secondary'), fontSize: 12, formatter: (p: { name: string; percent: number }) => `${p.name} ${p.percent}%` },
      data: (summary.value?.by_scene || []).map((s, i) => ({
        name: sceneLabels[s.scene] || s.scene,
        value: Number(s.cost.toFixed(4)),
        itemStyle: { color: palette()[i % palette().length] },
      })),
    }],
  }),
})

const quadrantEl = ref<HTMLElement | null>(null)
useChart(quadrantEl, {
  watchSource: scenePoints,
  buildOption: () => {
    const pts = scenePoints.value
    const meanCalls = pts.reduce((s, p) => s + p.calls, 0) / (pts.length || 1)
    const meanCost = pts.reduce((s, p) => s + p.cost, 0) / (pts.length || 1)
    return {
      ...baseChartOption(),
      grid: { left: 56, right: 24, top: 30, bottom: 32 },
      tooltip: {
        ...baseChartOption().tooltip, trigger: 'item',
        formatter: (p: { data: [string, number, number] }) => `${p.data[0]}：${p.data[1]} 次调用 / ¥${p.data[2].toFixed(4)}`,
      },
      xAxis: { type: 'value', name: '调用次数', nameTextStyle: { color: themeVar('--rh-text-tertiary') }, splitLine: { lineStyle: { color: themeVar('--rh-border-faint') } }, axisLabel: { color: themeVar('--rh-text-secondary'), fontSize: 12 } },
      yAxis: { type: 'value', name: '成本（元）', nameTextStyle: { color: themeVar('--rh-text-tertiary') }, splitLine: { lineStyle: { color: themeVar('--rh-border-faint') } }, axisLabel: { color: themeVar('--rh-text-secondary'), fontSize: 12 } },
      series: [
        {
          type: 'scatter', symbolSize: 18,
          label: { show: true, position: 'top', color: themeVar('--rh-text-secondary'), fontSize: 11, formatter: (p: { data: [string, number, number] }) => p.data[0] },
          data: pts.map((p) => ({ name: sceneLabels[p.scene] || p.scene, value: [p.calls, Number(p.cost.toFixed(4)), p.scene], itemStyle: { color: primary() } })),
          markLine: {
            silent: true, symbol: 'none',
            lineStyle: { color: themeVar('--rh-border'), type: 'dashed' },
            label: { color: themeVar('--rh-text-tertiary'), fontSize: 11 },
            data: [{ xAxis: meanCalls }, { yAxis: meanCost }],
          },
        },
      ],
    }
  },
})

const promptEl = ref<HTMLElement | null>(null)
useChart(promptEl, {
  watchSource: promptItems,
  buildOption: () => {
    const top = promptItems.value.slice(0, 10)
    return {
      ...baseChartOption(),
      grid: { left: 8, right: 40, top: 8, bottom: 20, containLabel: true },
      tooltip: { ...baseChartOption().tooltip, trigger: 'item' },
      xAxis: { type: 'value', splitLine: { lineStyle: { color: themeVar('--rh-border-faint') } }, axisLabel: { color: themeVar('--rh-text-secondary'), fontSize: 12 } },
      yAxis: {
        type: 'category',
        data: top.map((p) => p.title).reverse(),
        axisLabel: { color: themeVar('--rh-text-secondary'), fontSize: 12, width: 140, overflow: 'truncate' },
        axisTick: { show: false },
      },
      series: [{
        type: 'bar', barMaxWidth: 14, itemStyle: { color: primary(), borderRadius: 2 },
        label: { show: true, position: 'right', color: themeVar('--rh-text-secondary'), fontSize: 11 },
        data: top.map((p) => p.roi_score).reverse(),
      }],
    }
  },
  onClick: (name) => {
    const item = promptItems.value.find((p) => p.title === name)
    if (item) router.push(`/prompts/${item.prompt_id}`)
  },
})

// ── 数据加载 ─────────────────────────────────────
async function load() {
  loading.value = true
  try {
    const [s, t, n, p, q] = await Promise.all([
      roiApi.summary(days.value),
      roiApi.trend(days.value),
      roiApi.notes(days.value),
      roiApi.prompts(),
      roiApi.scenes(days.value),
    ])
    summary.value = s
    trendPoints.value = t.points
    noteItems.value = n.slice(0, 20)
    promptItems.value = p
    scenePoints.value = q
  } finally {
    loading.value = false
  }
}
function changeDays(v: number | string | boolean | undefined) {
  days.value = Number(v) || 30
  load()
}
onMounted(load)
</script>

<style scoped>
.roi-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 20px; margin-bottom: 28px; }
.eyebrow { margin-bottom: 7px; color: var(--rh-text-tertiary); font-size: 11px; font-weight: 700; letter-spacing: .04em; }
.roi-head h1 { font-family: var(--rh-font-display); font-size: clamp(26px, 3.4vw, 40px); line-height: 1.15; font-weight: 500; margin: 0; }
.sub { margin-top: 10px; color: var(--rh-text-secondary); font-size: 14px; }

.metric-strip { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 20px; margin-bottom: 20px; }
.metric { border: 1px solid var(--rh-border); border-radius: var(--rh-radius-md); background: var(--rh-bg-card); padding: 18px 20px; }
.metric small { display: block; color: var(--rh-text-tertiary); font-size: 12px; }
.metric strong { display: block; margin-top: 6px; font-family: var(--rh-font-display); font-size: 26px; font-weight: 500; font-variant-numeric: tabular-nums; }
.metric span { display: block; margin-top: 5px; color: var(--rh-text-tertiary); font-size: 12px; }

.roi-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; }
.span-2 { grid-column: span 2; }
.viz-chart--wide { min-height: 300px; }
.roi-table { width: 100%; }

@media (max-width: 800px) {
  .metric-strip { grid-template-columns: repeat(2, 1fr); }
  .roi-grid { grid-template-columns: 1fr; }
  .span-2 { grid-column: span 1; }
}
</style>

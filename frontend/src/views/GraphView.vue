<template>
  <div class="rh-page graph-page">
    <section class="graph-header animate-fade-in-up">
      <div>
        <p class="eyebrow">知识图谱</p>
        <h1>笔记之间的连接</h1>
        <p class="graph-copy">双向链接把笔记织成网络——连线越密的节点，越是知识网络的枢纽。</p>
      </div>
      <div class="graph-legend" aria-hidden="true">
        <span class="legend-item"><i class="legend-dot dot-personal"></i>个人笔记</span>
        <span class="legend-item"><i class="legend-dot dot-team"></i>团队笔记</span>
      </div>
    </section>

    <LoadingState v-if="loading" variant="card" />
    <EmptyState
      v-else-if="!nodes.length"
      :icon="Share"
      title="还没有可展示的笔记"
    >
      <router-link to="/notes"><el-button type="primary">去笔记库创建</el-button></router-link>
    </EmptyState>

    <template v-else>
      <section class="graph-stage animate-fade-in-up stagger-1" aria-label="笔记关系图谱">
        <div ref="chartRef" class="graph-canvas"></div>
        <p class="graph-hint">拖拽节点调整布局 · 滚轮缩放 · 点击节点打开笔记</p>
      </section>

      <!-- 无障碍数据摘要：图表内容以文本形式提供给屏幕阅读器 -->
      <table class="sr-only">
        <caption>笔记知识图谱数据摘要</caption>
        <thead>
          <tr><th scope="col">笔记</th><th scope="col">空间</th><th scope="col">连接数</th></tr>
        </thead>
        <tbody>
          <tr v-for="node in nodes" :key="node.id">
            <td>{{ node.title }}</td>
            <td>{{ node.team_name || '个人' }}</td>
            <td>{{ degreeMap[node.id] || 0 }}</td>
          </tr>
        </tbody>
      </table>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Share } from '@element-plus/icons-vue'
import { notesApi, type GraphNode, type GraphLink } from '../api/notes'
import { useChart, themeVar, baseChartOption } from '../composables/useChart'
import LoadingState from '../components/common/LoadingState.vue'
import EmptyState from '../components/common/EmptyState.vue'

const router = useRouter()
const chartRef = ref<HTMLElement | null>(null)
const loading = ref(true)
const nodes = ref<GraphNode[]>([])
const links = ref<GraphLink[]>([])

/** 连接度：节点大小与枢纽识别依据 */
const degreeMap = computed<Record<number, number>>(() => {
  const map: Record<number, number> = {}
  for (const link of links.value) {
    map[link.source] = (map[link.source] || 0) + 1
    map[link.target] = (map[link.target] || 0) + 1
  }
  return map
})

function buildOption(): Record<string, unknown> {
  const degree = degreeMap.value
  const data = nodes.value.map((node) => ({
    id: String(node.id),
    name: node.title,
    category: node.team_id != null ? 1 : 0,
    symbolSize: Math.min(16 + (degree[node.id] || 0) * 7, 64),
    value: degree[node.id] || 0,
  }))
  return {
    ...baseChartOption(),
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        draggable: true,
        data,
        links: links.value.map((l) => ({ source: String(l.source), target: String(l.target) })),
        categories: [
          { name: '个人笔记', itemStyle: { color: themeVar('--rh-primary', '#b03c22') } },
          { name: '团队笔记', itemStyle: { color: themeVar('--rh-ai-strong', '#7a9b1e') } },
        ],
        label: {
          show: true,
          color: themeVar('--rh-text-secondary'),
          fontSize: 11,
          position: 'bottom',
          formatter: (p: { name: string }) => (p.name.length > 10 ? p.name.slice(0, 10) + '…' : p.name),
        },
        lineStyle: {
          color: themeVar('--rh-border-strong', '#ccc'),
          width: 1.2,
          curveness: 0.12,
          opacity: 0.7,
        },
        emphasis: { focus: 'adjacency', label: { show: true } },
        force: { repulsion: 260, edgeLength: 90, gravity: 0.08 },
      },
    ],
    legend: {
      data: ['个人笔记', '团队笔记'],
      textStyle: { color: themeVar('--rh-text-secondary') },
      top: 6,
      left: 8,
      icon: 'circle',
      itemWidth: 9,
      itemHeight: 9,
    },
  }
}

const chartEl = ref(chartRef)
useChart(chartEl, {
  buildOption,
  onInstance: (chart) => {
    chart.on('click', (params) => {
      const id = Number((params.data as { id?: string } | undefined)?.id)
      if (id) router.push(`/notes?note=${id}`)
    })
  },
})

onMounted(async () => {
  try {
    const data = await notesApi.graph()
    nodes.value = data.nodes
    links.value = data.links
  } catch {
    nodes.value = []
    links.value = []
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.graph-page { display: flex; flex-direction: column; }
.graph-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 20px; flex-wrap: wrap; }
.eyebrow { margin-bottom: 7px; color: var(--rh-text-tertiary); font-size: 11px; font-weight: 700; letter-spacing: 0.04em; }
.graph-header h1 { font-family: var(--rh-font-display); font-size: clamp(26px, 3.4vw, 38px); font-weight: 500; line-height: 1.15; }
.graph-copy { margin-top: 10px; color: var(--rh-text-secondary); font-size: 14px; max-width: 560px; }
.graph-legend { display: flex; gap: 18px; padding-bottom: 6px; }
.legend-item { display: inline-flex; align-items: center; gap: 6px; color: var(--rh-text-tertiary); font-size: 12px; }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.dot-personal { background: var(--rh-primary); }
.dot-team { background: var(--rh-ai-strong); }

.graph-stage { margin-top: 24px; border: 1px solid var(--rh-border); border-radius: var(--rh-radius-md); background: var(--rh-bg-card); overflow: hidden; }
.graph-canvas { width: 100%; height: min(66vh, 640px); }
.graph-hint { padding: 10px 16px; border-top: 1px solid var(--rh-border-faint); color: var(--rh-text-tertiary); font-size: 12px; }
</style>

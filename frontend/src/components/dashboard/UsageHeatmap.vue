<template>
  <div class="viz-card">
    <div class="viz-head">
      <p class="eyebrow">近 120 天</p>
      <h3>提示词使用热力图</h3>
      <small>颜色越深，当日使用次数越多</small>
    </div>
    <div v-if="points.length" ref="chartEl" class="viz-chart"></div>
    <div v-if="!points.length" class="viz-empty">暂无使用记录</div>
  </div>
</template>

<script setup lang="ts">
/** 使用热力图：PromptUsageLog 近 120 天按日计数（日历热力图） */
import { computed, ref } from 'vue'
import type { HeatmapPoint } from '../../api/stats'
import { baseChartOption, themeVar, useChart } from '../../composables/useChart'

const props = defineProps<{ points: HeatmapPoint[] }>()

const chartEl = ref<HTMLElement | null>(null)

/** 日历区间：今天往前 119 天（含今天共 120 天），返回 [起, 止] */
function rangePair(): [string, string] {
  const fmt = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - 119)
  return [fmt(start), fmt(end)]
}

useChart(chartEl, {
  watchSource: computed(() => props.points),
  buildOption: () => {
    const maxCount = props.points.reduce((m, p) => Math.max(m, p.count), 1)
    return {
      ...baseChartOption(),
      tooltip: {
        ...baseChartOption().tooltip,
        formatter: (params: { value: [string, number] }) => `${params.value[0]}：使用 ${params.value[1]} 次`,
      },
      visualMap: {
        min: 0,
        max: maxCount,
        type: 'continuous',
        orient: 'horizontal',
        left: 'center',
        bottom: 0,
        itemWidth: 10,
        itemHeight: 80,
        text: ['多', '少'],
        textStyle: { color: themeVar('--rh-text-tertiary'), fontSize: 10 },
        inRange: { color: [themeVar('--rh-bg-inset', '#ebe9e1'), themeVar('--rh-primary', '#e85d3f')] },
      },
      calendar: {
        range: rangePair(),
        cellSize: ['auto', 14],
        left: 40,
        right: 16,
        top: 8,
        bottom: 40,
        itemStyle: {
          color: themeVar('--rh-bg-card'),
          borderColor: themeVar('--rh-border-faint'),
        },
        splitLine: { show: false },
        dayLabel: {
          nameMap: ['日', '一', '二', '三', '四', '五', '六'],
          firstDay: 1,
          color: themeVar('--rh-text-tertiary'),
          fontSize: 10,
        },
        monthLabel: {
          nameMap: 'ZH',
          color: themeVar('--rh-text-secondary'),
          fontSize: 11,
        },
        yearLabel: { show: false },
      },
      series: [
        {
          type: 'heatmap',
          coordinateSystem: 'calendar',
          data: props.points.map((p) => [p.date, p.count]),
        },
      ],
    }
  },
})
</script>

<style scoped>
.viz-card { border: 1px solid var(--rh-border); background: var(--rh-bg-card); padding: 20px 22px; display: flex; flex-direction: column; }
.viz-head { margin-bottom: 6px; }
.viz-head h3 { font-family: Georgia, 'Times New Roman', serif; font-size: 18px; font-weight: 500; margin: 0; }
.viz-head small { display: block; margin-top: 4px; color: var(--rh-text-tertiary); font-size: 12px; }
.eyebrow { margin: 0 0 5px; color: var(--rh-text-tertiary); font-size: 11px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
.viz-chart { flex: 1; min-height: 240px; }
.viz-empty { display: grid; place-items: center; flex: 1; min-height: 240px; color: var(--rh-text-tertiary); font-size: 13px; }
</style>

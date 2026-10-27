<template>
  <VizCard
    eyebrow="近 120 天"
    title="提示词使用热力图"
    hint="颜色越深，当日使用次数越多"
    empty="暂无使用记录"
    :has-data="points.length > 0"
  >
    <div ref="chartEl" class="viz-chart"></div>
    <!-- 无障碍数据摘要：屏幕阅读器可读取有使用记录的日期与次数 -->
    <template #sr-table>
      <table
        v-if="activePoints.length"
        class="viz-sr-table"
        aria-hidden="false"
        aria-label="提示词使用热力图数据摘要"
      >
        <caption class="sr-only">近 120 天各日提示词使用次数（仅列出有使用的日期）</caption>
        <thead>
          <tr>
            <th scope="col">日期</th>
            <th scope="col">使用次数</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in activePoints" :key="p.date">
            <td>{{ p.date }}</td>
            <td>{{ p.count }}</td>
          </tr>
        </tbody>
      </table>
    </template>
  </VizCard>
</template>

<script setup lang="ts">
/** 使用热力图：PromptUsageLog 近 120 天按日计数（日历热力图） */
import { computed, ref } from 'vue'
import type { HeatmapPoint } from '../../api/stats'
import { baseChartOption, themeVar, useChart } from '../../composables/useChart'
import VizCard from './VizCard.vue'

const props = defineProps<{ points: HeatmapPoint[] }>()

const chartEl = ref<HTMLElement | null>(null)

/** 将 #rrggbb 转为 rgba(r,g,b,alpha)，用于生成递增的主色深浅分级 */
function withAlpha(hex: string, alpha: number): string {
  const m = hex.trim().match(/^#?([0-9a-f]{6})$/i)
  if (!m) return hex // 非 6 位 hex（如 rgb() 或已带 alpha）直接原样返回
  const n = parseInt(m[1], 16)
  const r = (n >> 16) & 255
  const g = (n >> 8) & 255
  const b = n & 255
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

/** 日历区间：今天往前 119 天（含今天共 120 天），返回 [起, 止] */
function rangePair(): [string, string] {
  const fmt = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - 119)
  return [fmt(start), fmt(end)]
}

/** 数据摘要仅列出有使用记录的日子，保持表格简洁可读 */
const activePoints = computed(() => props.points.filter((p) => p.count > 0))

useChart(chartEl, {
  watchSource: computed(() => props.points),
  buildOption: () => {
    const primary = themeVar('--rh-primary', '#b03c22')
    // 递增的主色深浅：alpha 越大越接近实色主色
    const shades = [withAlpha(primary, 0.28), withAlpha(primary, 0.5), withAlpha(primary, 0.72), primary]
    return {
      ...baseChartOption(),
      tooltip: {
        ...baseChartOption().tooltip,
        formatter: (params: { value: [string, number] }) => `${params.value[0]}：使用 ${params.value[1]} 次`,
      },
      visualMap: {
        type: 'piecewise',
        orient: 'horizontal',
        left: 'center',
        bottom: 0,
        itemWidth: 10,
        itemHeight: 80,
        textStyle: { color: themeVar('--rh-text-secondary'), fontSize: 12 },
        // 离散分段：0 次为空白底色，其后各段主色逐渐加深，避免 0 与 1 难以区分
        pieces: [
          { min: 0, max: 0, label: '0 次', color: themeVar('--rh-bg-inset', '#ebe9e1') },
          { min: 1, max: 2, label: '1–2 次', color: shades[0] },
          { min: 3, max: 5, label: '3–5 次', color: shades[1] },
          { min: 6, max: 10, label: '6–10 次', color: shades[2] },
          { min: 11, label: '11+ 次', color: shades[3] },
        ],
        // 未命中分段时的兜底渐变
        inRange: { color: [themeVar('--rh-bg-inset', '#ebe9e1'), primary] },
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
          color: themeVar('--rh-text-secondary'),
          fontSize: 12,
        },
        monthLabel: {
          nameMap: 'ZH',
          color: themeVar('--rh-text-secondary'),
          fontSize: 12,
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

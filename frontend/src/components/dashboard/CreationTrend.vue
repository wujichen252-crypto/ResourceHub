<template>
  <div class="viz-card">
    <div class="viz-head">
      <p class="eyebrow">近 30 天</p>
      <h3>创作趋势</h3>
      <small>每日新增笔记与提示词</small>
    </div>
    <div v-if="points.length" ref="chartEl" class="viz-chart"></div>
    <div v-if="!points.length" class="viz-empty">暂无趋势数据</div>
  </div>
</template>

<script setup lang="ts">
/** 创作趋势：近 30 天笔记 / 提示词新增量双折线 */
import { computed, ref } from 'vue'
import type { TrendPoint } from '../../api/stats'
import { baseChartOption, themeVar, useChart } from '../../composables/useChart'

const props = defineProps<{ points: TrendPoint[] }>()

const chartEl = ref<HTMLElement | null>(null)

useChart(chartEl, {
  watchSource: computed(() => props.points),
  buildOption: () => {
    const primary = themeVar('--rh-primary', '#e85d3f')
    const ai = themeVar('--rh-ai-strong', '#789415')
    return {
      ...baseChartOption(),
      grid: { left: 36, right: 14, top: 34, bottom: 26 },
      legend: {
        top: 0,
        right: 0,
        itemWidth: 14,
        textStyle: { color: themeVar('--rh-text-secondary'), fontSize: 11 },
      },
      tooltip: { ...baseChartOption().tooltip, trigger: 'axis' },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: props.points.map((p) => p.date.slice(5)),
        axisLine: { lineStyle: { color: themeVar('--rh-border') } },
        axisTick: { show: false },
        axisLabel: { color: themeVar('--rh-text-tertiary'), fontSize: 10, interval: 'auto' },
      },
      yAxis: {
        type: 'value',
        minInterval: 1,
        splitLine: { lineStyle: { color: themeVar('--rh-border-faint') } },
        axisLabel: { color: themeVar('--rh-text-tertiary'), fontSize: 10 },
      },
      series: [
        {
          name: '笔记',
          type: 'line',
          smooth: true,
          symbol: 'none',
          lineStyle: { color: primary, width: 2 },
          areaStyle: { color: primary, opacity: 0.08 },
          data: props.points.map((p) => p.notes),
        },
        {
          name: '提示词',
          type: 'line',
          smooth: true,
          symbol: 'none',
          lineStyle: { color: ai, width: 2 },
          areaStyle: { color: ai, opacity: 0.08 },
          data: props.points.map((p) => p.prompts),
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

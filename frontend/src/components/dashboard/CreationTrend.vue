<template>
  <VizCard
    eyebrow="近 30 天"
    title="创作趋势"
    hint="每日新增笔记与提示词"
    empty="暂无趋势数据"
    :has-data="points.length > 0"
  >
    <div ref="chartEl" class="viz-chart"></div>
    <!-- 无障碍数据摘要：屏幕阅读器可读取每日新增量 -->
    <template #sr-table>
      <table
        v-if="points.length"
        class="viz-sr-table"
        aria-hidden="false"
        aria-label="创作趋势数据摘要"
      >
        <caption class="sr-only">近 30 天每日新增笔记与提示词数量</caption>
        <thead>
          <tr>
            <th scope="col">日期</th>
            <th scope="col">笔记</th>
            <th scope="col">提示词</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in points" :key="p.date">
            <td>{{ p.date }}</td>
            <td>{{ p.notes }}</td>
            <td>{{ p.prompts }}</td>
          </tr>
        </tbody>
      </table>
    </template>
  </VizCard>
</template>

<script setup lang="ts">
/** 创作趋势：近 30 天笔记 / 提示词新增量双折线 */
import { computed, ref } from 'vue'
import type { TrendPoint } from '../../api/stats'
import { baseChartOption, themeVar, useChart } from '../../composables/useChart'
import VizCard from './VizCard.vue'

const props = defineProps<{ points: TrendPoint[] }>()

const chartEl = ref<HTMLElement | null>(null)

/** 全站统一调色板（顺序：主色 → AI 强调 → 成功 → 警告 → 信息 → 主色激活） */
const palette = computed(() => [
  themeVar('--rh-primary', '#b03c22'),
  themeVar('--rh-ai-strong', '#5f7410'),
  themeVar('--rh-success', '#3f8f6b'),
  themeVar('--rh-warning', '#9a6a1c'),
  themeVar('--rh-info', '#6a7268'),
  themeVar('--rh-primary-active', '#7f2714'),
])

useChart(chartEl, {
  watchSource: computed(() => props.points),
  buildOption: () => {
    // 与全站调色板保持同一色序：序号 0 为主色，序号 1 为 AI 强调色
    const primary = palette.value[0]
    const ai = palette.value[1]
    return {
      ...baseChartOption(),
      grid: { left: 36, right: 14, top: 34, bottom: 26 },
      legend: {
        top: 0,
        right: 0,
        itemWidth: 14,
        textStyle: { color: themeVar('--rh-text-secondary'), fontSize: 12 },
      },
      tooltip: { ...baseChartOption().tooltip, trigger: 'axis' },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: props.points.map((p) => p.date.slice(5)),
        axisLine: { lineStyle: { color: themeVar('--rh-border') } },
        axisTick: { show: false },
        axisLabel: { color: themeVar('--rh-text-secondary'), fontSize: 12, interval: 'auto' },
      },
      yAxis: {
        type: 'value',
        minInterval: 1,
        splitLine: { lineStyle: { color: themeVar('--rh-border-faint') } },
        axisLabel: { color: themeVar('--rh-text-secondary'), fontSize: 12 },
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

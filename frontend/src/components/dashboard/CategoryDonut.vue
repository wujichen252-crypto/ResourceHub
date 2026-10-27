<template>
  <VizCard
    eyebrow="资源构成"
    title="分类分布"
    hint="笔记按一级分类统计"
    empty="暂无分类数据"
    :has-data="items.length > 0"
  >
    <div ref="chartEl" class="viz-chart"></div>
    <!-- 无障碍数据摘要：屏幕阅读器可读取分类与数量 -->
    <template #sr-table>
      <table
        v-if="items.length"
        class="viz-sr-table"
        aria-hidden="false"
        aria-label="分类分布数据摘要"
      >
        <caption class="sr-only">笔记一级分类及其数量</caption>
        <thead>
          <tr>
            <th scope="col">分类</th>
            <th scope="col">数量</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="d in items" :key="d.name">
            <td>{{ d.name }}</td>
            <td>{{ d.value }}</td>
          </tr>
        </tbody>
      </table>
    </template>
  </VizCard>
</template>

<script setup lang="ts">
/** 分类分布：一级分类（含未分类）环形图 */
import { computed, ref } from 'vue'
import type { DistributionItem } from '../../api/stats'
import { baseChartOption, themeVar, useChart } from '../../composables/useChart'
import VizCard from './VizCard.vue'

const props = defineProps<{ items: DistributionItem[] }>()

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
  watchSource: computed(() => props.items),
  buildOption: () => ({
    ...baseChartOption(),
    color: palette.value,
    tooltip: { ...baseChartOption().tooltip, trigger: 'item', formatter: '{b}: {c}（{d}%）' },
    legend: {
      bottom: 0,
      icon: 'circle',
      itemWidth: 8,
      textStyle: { color: themeVar('--rh-text-secondary'), fontSize: 12 },
    },
    series: [
      {
        type: 'pie',
        radius: ['45%', '70%'],
        center: ['50%', '44%'],
        avoidLabelOverlap: true,
        itemStyle: { borderColor: themeVar('--rh-bg-card'), borderWidth: 2 },
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 13, fontWeight: 700, color: themeVar('--rh-text-primary') } },
        data: props.items.map((d) => ({ name: d.name, value: d.value })),
      },
    ],
  }),
})
</script>

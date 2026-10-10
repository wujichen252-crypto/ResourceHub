<template>
  <div class="viz-card">
    <div class="viz-head">
      <p class="eyebrow">资源构成</p>
      <h3>分类分布</h3>
      <small>笔记按一级分类统计</small>
    </div>
    <div v-if="items.length" ref="chartEl" class="viz-chart"></div>
    <div v-if="!items.length" class="viz-empty">暂无分类数据</div>
  </div>
</template>

<script setup lang="ts">
/** 分类分布：一级分类（含未分类）环形图 */
import { computed, ref } from 'vue'
import type { DistributionItem } from '../../api/stats'
import { baseChartOption, themeVar, useChart } from '../../composables/useChart'

const props = defineProps<{ items: DistributionItem[] }>()

const chartEl = ref<HTMLElement | null>(null)

const palette = computed(() => [
  themeVar('--rh-primary', '#e85d3f'),
  themeVar('--rh-ai-strong', '#789415'),
  themeVar('--rh-success', '#3f8f6b'),
  themeVar('--rh-warning', '#c8892e'),
  themeVar('--rh-info', '#788079'),
  themeVar('--rh-primary-active', '#a93c28'),
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
      textStyle: { color: themeVar('--rh-text-secondary'), fontSize: 11 },
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

<style scoped>
.viz-card { border: 1px solid var(--rh-border); background: var(--rh-bg-card); padding: 20px 22px; display: flex; flex-direction: column; }
.viz-head { margin-bottom: 6px; }
.viz-head h3 { font-family: Georgia, 'Times New Roman', serif; font-size: 18px; font-weight: 500; margin: 0; }
.viz-head small { display: block; margin-top: 4px; color: var(--rh-text-tertiary); font-size: 12px; }
.eyebrow { margin: 0 0 5px; color: var(--rh-text-tertiary); font-size: 11px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
.viz-chart { flex: 1; min-height: 240px; }
.viz-empty { display: grid; place-items: center; flex: 1; min-height: 240px; color: var(--rh-text-tertiary); font-size: 13px; }
</style>

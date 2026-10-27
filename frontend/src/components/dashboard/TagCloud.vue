<template>
  <VizCard
    eyebrow="标签分布"
    title="标签云"
    hint="点击标签可在笔记中筛选"
    empty="暂无带标签的内容"
    :has-data="items.length > 0"
  >
    <div ref="chartEl" class="viz-chart"></div>
    <!-- 无障碍数据摘要：屏幕阅读器可读取标签与出现次数 -->
    <template #sr-table>
      <table
        v-if="items.length"
        class="viz-sr-table"
        aria-hidden="false"
        aria-label="标签分布数据摘要"
      >
        <caption class="sr-only">标签云数据摘要：各标签及其出现次数</caption>
        <thead>
          <tr>
            <th scope="col">标签</th>
            <th scope="col">次数</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in items" :key="t.name">
            <td>{{ t.name }}</td>
            <td>{{ t.value }}</td>
          </tr>
        </tbody>
      </table>
    </template>
  </VizCard>
</template>

<script setup lang="ts">
/** 标签云：笔记 + 提示词标签聚合，点击标签跳转笔记页并按标签过滤 */
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useNotesStore } from '../../stores/notes'
import type { TagItem } from '../../api/stats'
import { baseChartOption, themeVar, useChart } from '../../composables/useChart'
import VizCard from './VizCard.vue'

const props = defineProps<{ items: TagItem[] }>()

const router = useRouter()
const notesStore = useNotesStore()
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
    series: [
      {
        type: 'wordCloud',
        shape: 'circle',
        left: 'center',
        top: 'center',
        width: '92%',
        height: '88%',
        sizeRange: [12, 34],
        rotationRange: [0, 0],
        gridSize: 8,
        drawOutOfBound: false,
        textStyle: {
          fontFamily: "'Noto Sans SC', 'PingFang SC', sans-serif",
          fontWeight: 700,
          // 按标签序号顺序取色（而非随机），保证同一标签颜色稳定、且与顺序一致
          color: (params: { dataIndex: number }) => palette.value[params.dataIndex % palette.value.length],
        },
        emphasis: { textStyle: { textShadowBlur: 4, textShadowColor: themeVar('--rh-border-strong') } },
        data: props.items.map((t) => ({ name: t.name, value: t.value })),
      },
    ],
  }),
  onClick: (name) => {
    notesStore.setTag(name)
    router.push('/notes')
  },
})
</script>

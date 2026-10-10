<template>
  <div class="viz-card">
    <div class="viz-head">
      <p class="eyebrow">标签分布</p>
      <h3>标签云</h3>
      <small>点击标签可在笔记中筛选</small>
    </div>
    <div v-if="items.length" ref="chartEl" class="viz-chart"></div>
    <div v-if="!items.length" class="viz-empty">暂无带标签的内容</div>
  </div>
</template>

<script setup lang="ts">
/** 标签云：笔记 + 提示词标签聚合，点击标签跳转笔记页并按标签过滤 */
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useNotesStore } from '../../stores/notes'
import type { TagItem } from '../../api/stats'
import { baseChartOption, themeVar, useChart } from '../../composables/useChart'

const props = defineProps<{ items: TagItem[] }>()

const router = useRouter()
const notesStore = useNotesStore()
const chartEl = ref<HTMLElement | null>(null)

const palette = computed(() => [
  themeVar('--rh-primary', '#e85d3f'),
  themeVar('--rh-ai-strong', '#789415'),
  themeVar('--rh-success', '#3f8f6b'),
  themeVar('--rh-warning', '#c8892e'),
  themeVar('--rh-info', '#788079'),
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
          color: () => palette.value[Math.floor(Math.random() * palette.value.length)],
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

<style scoped>
.viz-card { border: 1px solid var(--rh-border); background: var(--rh-bg-card); padding: 20px 22px; display: flex; flex-direction: column; }
.viz-head { margin-bottom: 6px; }
.viz-head h3 { font-family: Georgia, 'Times New Roman', serif; font-size: 18px; font-weight: 500; margin: 0; }
.viz-head small { display: block; margin-top: 4px; color: var(--rh-text-tertiary); font-size: 12px; }
.eyebrow { margin: 0 0 5px; color: var(--rh-text-tertiary); font-size: 11px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
.viz-chart { flex: 1; min-height: 240px; }
.viz-empty { display: grid; place-items: center; flex: 1; min-height: 240px; color: var(--rh-text-tertiary); font-size: 13px; }
</style>

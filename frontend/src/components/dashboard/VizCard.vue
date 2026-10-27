<template>
  <div class="viz-card">
    <div class="viz-head">
      <div class="viz-head-main">
        <p class="eyebrow">{{ eyebrow }}</p>
        <h3 class="viz-title">{{ title }}</h3>
        <small v-if="hint">{{ hint }}</small>
      </div>
      <!-- 可选右上角自定义区域（如放图例、切换），无内容时自动隐藏 -->
      <div v-if="$slots.aside" class="viz-aside">
        <slot name="aside" />
      </div>
    </div>
    <!-- 图表主体：有数据时渲染默认插槽，否则显示空态 -->
    <slot v-if="hasData" />
    <div v-else class="viz-empty">{{ empty }}</div>
    <!-- 无障碍数据摘要：表格结构由各图表自行提供 -->
    <slot name="sr-table" />
  </div>
</template>

<script setup lang="ts">
/** 仪表盘可视化卡片外壳：统一「小标 + 标题 + 说明」头部、图表主体、空态与无障碍数据表容器 */
withDefaults(
  defineProps<{
    /** 小标，如「标签分布」 */
    eyebrow: string
    /** 主标题，如「标签云」 */
    title: string
    /** 说明小字，如「点击标签可在笔记中筛选」 */
    hint?: string
    /** 空态文案，默认「暂无数据」 */
    empty?: string
    /** 是否有数据；false 时渲染空态 */
    hasData?: boolean
  }>(),
  { empty: '暂无数据', hasData: true },
)
</script>

<style scoped>
.viz-card { border: 1px solid var(--rh-border); background: var(--rh-bg-card); border-radius: var(--rh-radius-md); padding: 20px 22px; display: flex; flex-direction: column; }
.viz-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 6px; }
.viz-head-main { min-width: 0; }
.eyebrow { margin: 0 0 5px; color: var(--rh-text-tertiary); font-size: 11px; font-weight: 800; }
.viz-title { font-family: var(--rh-font-display); font-size: 18px; font-weight: 500; letter-spacing: 0; margin: 0; }
.viz-head small { display: block; margin-top: 4px; color: var(--rh-text-tertiary); font-size: 12px; }
.viz-aside { flex-shrink: 0; }
.viz-empty { display: grid; place-items: center; flex: 1; min-height: 240px; color: var(--rh-text-tertiary); font-size: 13px; }
/* 图表容器与数据表均由插槽传入，需用 :deep 穿透作用域才能生效 */
:deep(.viz-chart) { flex: 1; min-height: 240px; }
/* 无障碍数据摘要：仅供屏幕阅读器读取，不在页面上占位，避免长表格把卡片拉得过高 */
:deep(.viz-sr-table) { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
</style>

<template>
  <div class="rh-empty" :style="{ minHeight }">
    <el-icon v-if="icon" :size="44" class="rh-empty__icon">
      <component :is="icon" />
    </el-icon>
    <p class="rh-empty__title">{{ title }}</p>
    <p v-if="description" class="rh-empty__desc">{{ description }}</p>
    <div v-if="$slots.default" class="rh-empty__actions">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 空状态：全站统一的"暂无内容"呈现。
 * 原先 Plaza / PromptList / NoteContent / PlazaDetail 各写一套（padding 60/80px、字号 15/16px 混用），
 * 此处收敛为一套：图标 → 标题 → 说明 → 操作区。
 */
import type { Component } from 'vue'

withDefaults(
  defineProps<{
    /** 顶部图标组件（来自 @element-plus/icons-vue） */
    icon?: Component
    /** 主文案，说明"这里没有内容" */
    title: string
    /** 补充说明，如"去创建一个"之类的引导 */
    description?: string
    /** 容器最小高度，默认 400px 便于在内容区居中 */
    minHeight?: string
  }>(),
  { minHeight: '400px' },
)
</script>

<style scoped>
.rh-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px 24px;
  text-align: center;
  color: var(--rh-text-tertiary);
}

.rh-empty__icon {
  color: var(--rh-text-tertiary);
  margin-bottom: 4px;
}

.rh-empty__title {
  margin: 0;
  font-size: 15px;
  font-weight: 500;
  color: var(--rh-text-secondary);
}

.rh-empty__desc {
  margin: 0;
  max-width: 420px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--rh-text-tertiary);
}

.rh-empty__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 8px;
}
</style>

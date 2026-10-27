<template>
  <div class="rh-loading" :class="`is-${variant}`" role="status" aria-live="polite">
    <span class="sr-only">{{ label }}</span>

    <!-- 卡片网格：用于笔记卡片、提示词卡片、广场列表 -->
    <template v-if="variant === 'card'">
      <div v-for="i in count" :key="i" class="rh-loading__card">
        <el-skeleton animated>
          <template #template>
            <el-skeleton-item variant="text" class="rh-loading__line" style="width: 42%; height: 18px" />
            <el-skeleton-item variant="text" class="rh-loading__line" style="width: 100%; margin-top: 14px" />
            <el-skeleton-item variant="text" class="rh-loading__line" style="width: 84%" />
            <el-skeleton-item variant="text" class="rh-loading__line" style="width: 58%; margin-top: 14px" />
          </template>
        </el-skeleton>
      </div>
    </template>

    <!-- 行列表：用于侧栏、版本列表等窄容器 -->
    <template v-else-if="variant === 'row'">
      <div v-for="i in count" :key="i" class="rh-loading__row">
        <el-skeleton animated :rows="1" />
      </div>
    </template>

    <!-- 详情页：标题 + 若干正文段 -->
    <template v-else-if="variant === 'detail'">
      <el-skeleton animated>
        <template #template>
          <el-skeleton-item variant="text" style="width: 55%; height: 28px" />
          <el-skeleton-item variant="text" style="width: 32%; margin-top: 16px" />
          <el-skeleton-item variant="text" style="width: 100%; margin-top: 28px" />
          <el-skeleton-item variant="text" style="width: 96%" />
          <el-skeleton-item variant="text" style="width: 88%" />
          <el-skeleton-item variant="text" style="width: 94%; margin-top: 20px" />
          <el-skeleton-item variant="text" style="width: 70%" />
        </template>
      </el-skeleton>
    </template>

    <!-- 图表：单一矩形占位，保持与图表容器同高，避免加载完成后的布局跳动 -->
    <template v-else>
      <el-skeleton-item variant="image" class="rh-loading__chart" />
    </template>
  </div>
</template>

<script setup lang="ts">
/**
 * 加载状态：用骨架屏替代原先散落的「转圈图标 + 空 div v-loading」。
 * 骨架屏提前勾勒出内容形状，感知等待时间更短，且避免加载完成时的布局跳动。
 */
withDefaults(
  defineProps<{
    /** 骨架形态：card 卡片网格 / row 行列表 / detail 详情页 / chart 图表块 */
    variant?: 'card' | 'row' | 'detail' | 'chart'
    /** 重复数量（card 与 row 形态有效） */
    count?: number
    /** 屏幕阅读器播报文案 */
    label?: string
  }>(),
  { variant: 'detail', count: 6, label: '内容加载中' },
)
</script>

<style scoped>
.rh-loading {
  width: 100%;
}

.rh-loading.is-card {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}

.rh-loading__card {
  padding: 20px;
  border: 1px solid var(--rh-border-faint);
  border-radius: var(--rh-radius-md);
  background: var(--rh-bg-card);
}

.rh-loading.is-row {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.rh-loading__row {
  padding: 10px 12px;
  border-radius: var(--rh-radius-sm);
  background: var(--rh-bg-subtle);
}

.rh-loading.is-detail {
  padding: 8px 0;
}

.rh-loading__chart {
  width: 100%;
  height: 260px;
  border-radius: var(--rh-radius-md);
}

/* 骨架条目自身带 margin-top 时，Element 默认的间距会被覆盖，这里统一收敛 */
.rh-loading__line + .rh-loading__line {
  margin-top: 10px;
}
</style>

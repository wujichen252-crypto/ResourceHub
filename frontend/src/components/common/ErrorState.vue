<template>
  <div class="rh-error" role="alert">
    <el-icon :size="40" class="rh-error__icon"><WarningFilled /></el-icon>
    <p class="rh-error__title">{{ title }}</p>
    <p v-if="description" class="rh-error__desc">{{ description }}</p>
    <el-button v-if="retryable" @click="emit('retry')">
      <el-icon><RefreshRight /></el-icon> 重试
    </el-button>
  </div>
</template>

<script setup lang="ts">
/**
 * 错误状态：全站统一的失败呈现。
 * 原先失败时只有一条 ElMessage toast，页面主体停留在上一个状态或空白，用户无法判断"是加载失败还是真的没数据"。
 */
import { WarningFilled, RefreshRight } from '@element-plus/icons-vue'

withDefaults(
  defineProps<{
    /** 主文案 */
    title?: string
    /** 失败原因或建议 */
    description?: string
    /** 是否展示「重试」按钮（由父组件监听 retry 事件） */
    retryable?: boolean
  }>(),
  { title: '加载失败', description: '请检查网络连接后重试', retryable: true },
)

const emit = defineEmits<{ retry: [] }>()
</script>

<style scoped>
.rh-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  min-height: 320px;
  padding: 40px 24px;
  text-align: center;
}

.rh-error__icon {
  color: var(--rh-danger);
  margin-bottom: 4px;
}

.rh-error__title {
  margin: 0;
  font-size: 15px;
  font-weight: 500;
  color: var(--rh-text-primary);
}

.rh-error__desc {
  margin: 0 0 8px;
  max-width: 420px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--rh-text-secondary);
}
</style>

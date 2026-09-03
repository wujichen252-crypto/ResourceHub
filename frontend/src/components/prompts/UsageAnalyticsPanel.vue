<template>
  <el-dialog
    v-model="visible"
    title="用量分析"
    width="600px"
    @open="loadData"
  >
    <div v-if="loading" v-loading="loading" class="loading" />

    <template v-if="data && !loading">
      <!-- Total -->
      <el-card shadow="never" class="stat-card">
        <div class="stat-value">{{ data.total_uses }}</div>
        <div class="stat-label">总使用次数</div>
      </el-card>

      <!-- Top 10 -->
      <el-card shadow="never" class="section-card">
        <template #header><span>最常用的提示词</span></template>
        <el-table :data="data.most_used" size="small" v-if="data.most_used.length">
          <el-table-column label="#" type="index" width="50" />
          <el-table-column label="标题" prop="title" />
          <el-table-column label="使用次数" prop="count" width="100" align="right" />
        </el-table>
        <div v-else class="empty-section">暂无使用记录</div>
      </el-card>

      <!-- Daily Trend -->
      <el-card shadow="never" class="section-card">
        <template #header><span>近 30 天趋势</span></template>
        <div v-if="data.daily_usage.length" class="daily-chart">
          <div
            v-for="day in data.daily_usage"
            :key="day.date"
            class="daily-bar-row"
          >
            <span class="daily-date">{{ formatDate(day.date) }}</span>
            <div class="daily-bar-track">
              <div
                class="daily-bar"
                :style="{ width: barWidth(day.count) }"
              />
            </div>
            <span class="daily-count">{{ day.count }}</span>
          </div>
        </div>
        <div v-else class="empty-section">近 30 天无使用记录</div>
      </el-card>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { usePromptsStore } from '../../stores/prompts'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const visible = ref(props.modelValue)
const loading = ref(false)

import { watch } from 'vue'
watch(() => props.modelValue, (v) => { visible.value = v })
watch(visible, (v) => emit('update:modelValue', v))

const promptsStore = usePromptsStore()
const data = computed(() => promptsStore.usageAnalytics)

const maxCount = computed(() => {
  if (!data.value?.daily_usage.length) return 1
  return Math.max(...data.value.daily_usage.map((d) => d.count), 1)
})

function barWidth(count: number): string {
  return `${(count / maxCount.value) * 100}%`
}

function formatDate(dateStr: string) {
  if (!dateStr) return ''
  const d = new Date(dateStr + 'T00:00:00')
  return `${d.getMonth() + 1}/${d.getDate()}`
}

async function loadData() {
  loading.value = true
  try {
    await promptsStore.fetchUsageAnalytics()
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.loading {
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-card {
  margin-bottom: 16px;
  text-align: center;
  padding: 16px 0;
}

.stat-value {
  font-size: 36px;
  font-weight: 700;
  color: var(--rh-primary);
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: var(--rh-text-tertiary);
  margin-top: 4px;
}

.section-card {
  margin-bottom: 16px;
}

.empty-section {
  text-align: center;
  color: var(--rh-text-tertiary);
  padding: 24px 0;
  font-size: 14px;
}

/* Daily Chart */
.daily-chart {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.daily-bar-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.daily-date {
  width: 44px;
  text-align: right;
  color: var(--rh-text-tertiary);
  flex-shrink: 0;
}

.daily-bar-track {
  flex: 1;
  height: 16px;
  background: var(--rh-bg-subtle);
  border-radius: 4px;
  overflow: hidden;
}

.daily-bar {
  height: 100%;
  background: var(--rh-primary);
  border-radius: 4px;
  transition: width 0.3s ease;
  min-width: 2px;
}

.daily-count {
  width: 28px;
  text-align: right;
  color: var(--rh-text-secondary);
  font-weight: 500;
  flex-shrink: 0;
}
</style>

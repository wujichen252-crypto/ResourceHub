<template>
  <div class="identity-panel">
    <div class="memory-toolbar">
      <el-radio-group v-model="filter" size="small" @change="reload">
        <el-radio-button value="all">全部</el-radio-button>
        <el-radio-button value="fact">事实</el-radio-button>
        <el-radio-button value="preference">偏好</el-radio-button>
        <el-radio-button value="goal">目标</el-radio-button>
        <el-radio-button value="event">经历</el-radio-button>
      </el-radio-group>
      <el-input
        v-model="keyword"
        size="small"
        clearable
        placeholder="搜索记忆"
        aria-label="搜索记忆"
        @input="handleSearch"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
    </div>

    <div class="memory-meta">
      <span>{{ identity.memories.length }} 条记忆</span>
      <div class="memory-actions">
        <el-button size="small" text type="danger" :disabled="!identity.memories.length" @click="clearAll">
          <el-icon><Delete /></el-icon>
          清空
        </el-button>
        <el-button size="small" @click="showAdd = !showAdd">
          <el-icon><Plus /></el-icon>
          添加
        </el-button>
      </div>
    </div>

    <div v-if="showAdd" class="memory-add">
      <el-input
        v-model="draft.content"
        type="textarea"
        :rows="2"
        maxlength="2000"
        placeholder="例如：我想在三个月内完成一个全栈项目"
      />
      <div class="memory-add__row">
        <el-select v-model="draft.memory_type" size="small" aria-label="记忆类型">
          <el-option label="事实" value="fact" />
          <el-option label="偏好" value="preference" />
          <el-option label="目标" value="goal" />
          <el-option label="经历" value="event" />
        </el-select>
        <span class="importance-label">重要度</span>
        <el-rate v-model="draft.importance" :max="5" :allow-half="false" />
        <el-button
          type="primary"
          size="small"
          :loading="identity.saving"
          :disabled="!draft.content.trim()"
          @click="add"
        >
          记住
        </el-button>
      </div>
    </div>

    <LoadingState v-if="identity.loading" variant="row" :count="3" label="正在读取记忆" />
    <ErrorState
      v-else-if="identity.error"
      title="记忆加载失败"
      :description="identity.error"
      @retry="reload"
    />
    <EmptyState
      v-else-if="!identity.memories.length"
      :icon="Collection"
      title="还没有记忆"
      description="在对话里说出你的目标、偏好或经历，我会把它们记下来；也可以手动添加。"
      min-height="0"
    />
    <ul v-else class="memory-list">
      <li v-for="memory in identity.memories" :key="memory.id" class="memory-item">
        <div class="memory-item__head">
          <span class="memory-type" :class="`type-${memory.memory_type}`">{{ typeLabel(memory.memory_type) }}</span>
          <span class="memory-source">{{ memory.source === 'conversation' ? '对话记住' : memory.source === 'manual' ? '手动添加' : '来自笔记' }}</span>
          <el-button
            text
            size="small"
            type="danger"
            class="memory-delete"
            :aria-label="`删除记忆：${memory.content}`"
            @click="remove(memory.id)"
          >
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
        <p class="memory-content">{{ memory.content }}</p>
        <div class="memory-item__foot">
          <span class="importance-dots" :aria-label="`重要度 ${memory.importance} / 5`">
            <i v-for="n in 5" :key="n" :class="{ filled: n <= memory.importance }" />
          </span>
          <span>{{ formatRelative(memory.created_at) }}</span>
        </div>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Collection, Delete, Plus, Search } from '@element-plus/icons-vue'
import EmptyState from '../common/EmptyState.vue'
import ErrorState from '../common/ErrorState.vue'
import LoadingState from '../common/LoadingState.vue'
import { useAgentIdentityStore } from '../../stores/agentIdentity'
import { formatRelative } from '../../utils/format'
import type { AgentMemoryType } from '../../api/ai'

const identity = useAgentIdentityStore()
const filter = ref('all')
const keyword = ref('')
const showAdd = ref(false)
const draft = reactive({
  content: '',
  memory_type: 'fact' as AgentMemoryType,
  importance: 3,
})

let searchTimer: number | undefined

const labels: Record<string, string> = {
  fact: '事实',
  preference: '偏好',
  goal: '目标',
  event: '经历',
}

function typeLabel(type: string): string {
  return labels[type] ?? '记忆'
}

function reload(): Promise<void> {
  return identity.loadMemories(
    filter.value === 'all' ? undefined : filter.value,
    keyword.value.trim() || undefined,
  )
}

function handleSearch(): void {
  if (searchTimer !== undefined) window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(() => {
    void reload()
  }, 300)
}

async function add(): Promise<void> {
  if (!draft.content.trim()) return
  await identity.addMemory({
    content: draft.content.trim(),
    memory_type: draft.memory_type,
    importance: draft.importance,
  })
  draft.content = ''
  draft.importance = 3
  showAdd.value = false
  ElMessage.success('已记住')
}

function remove(id: number): void {
  ElMessageBox.confirm('删除后这条记忆不会再被用于回答，确定删除吗？', '删除记忆', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'error',
  })
    .then(async () => {
      await identity.removeMemory(id)
      ElMessage.success('记忆已删除')
    })
    .catch(() => {})
}

function clearAll(): void {
  ElMessageBox.confirm('清空后所有长期记忆都会消失，这个操作不可恢复，确定继续吗？', '清空记忆', {
    confirmButtonText: '全部清空',
    cancelButtonText: '取消',
    type: 'error',
  })
    .then(async () => {
      await identity.clearMemories()
      ElMessage.success('记忆已清空')
    })
    .catch(() => {})
}
</script>

<style scoped>
.identity-panel {
  display: grid;
  gap: var(--rh-space-base);
  min-height: 200px;
}

.memory-toolbar {
  display: grid;
  gap: var(--rh-space-sm);
}

.memory-toolbar :deep(.el-radio-group) {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.memory-toolbar :deep(.el-input) {
  width: 100%;
}

.memory-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--rh-space-sm);
  color: var(--rh-text-tertiary);
  font-size: var(--rh-fs-sm);
}

.memory-actions {
  display: flex;
  gap: 2px;
}

.memory-add {
  display: grid;
  gap: var(--rh-space-sm);
  padding: var(--rh-space-sm);
  border: 1px solid var(--rh-border);
  border-radius: var(--rh-radius-sm);
  background: var(--rh-bg-subtle);
}

.memory-add__row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--rh-space-sm);
}

.memory-add__row :deep(.el-select) {
  width: 92px;
}

.importance-label {
  color: var(--rh-text-tertiary);
  font-size: var(--rh-fs-sm);
}

.memory-add__row :deep(.el-button) {
  margin-left: auto;
}

.memory-list {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.memory-item {
  padding: 11px 12px;
  border: 1px solid var(--rh-border);
  border-radius: var(--rh-radius-sm);
  background: var(--rh-bg-card);
}

.memory-item__head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.memory-type {
  padding: 2px 7px;
  border-radius: var(--rh-radius-xs);
  background: var(--rh-bg-active);
  color: var(--rh-primary);
  font-size: var(--rh-fs-xs);
  font-weight: 700;
}

.memory-type.type-goal {
  color: var(--rh-ai-strong);
}

.memory-type.type-preference {
  color: var(--rh-success);
}

.memory-source {
  color: var(--rh-text-tertiary);
  font-size: var(--rh-fs-xs);
}

.memory-delete {
  margin-left: auto;
}

.memory-content {
  margin: 8px 0;
  color: var(--rh-text-primary);
  font-size: var(--rh-fs-md);
  line-height: var(--rh-lh-base);
  word-break: break-word;
}

.memory-item__foot {
  display: flex;
  align-items: center;
  gap: var(--rh-space-sm);
  color: var(--rh-text-tertiary);
  font-size: var(--rh-fs-xs);
}

.importance-dots {
  display: inline-flex;
  gap: 3px;
}

.importance-dots i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--rh-border-strong);
}

.importance-dots i.filled {
  background: var(--rh-primary);
}
</style>

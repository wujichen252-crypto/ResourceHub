<template>
  <div class="identity-panel">
    <div class="inbox-head">
      <div>
        <strong>主动消息</strong>
        <p>每日回顾与目标提醒会出现在这里。</p>
      </div>
      <el-button size="small" :loading="scanning" @click="scan">
        <el-icon><Refresh /></el-icon>
        主动扫描
      </el-button>
    </div>

    <LoadingState v-if="identity.loading" variant="row" :count="3" label="正在读取主动消息" />
    <ErrorState
      v-else-if="identity.error"
      title="主动消息加载失败"
      :description="identity.error"
      @retry="reload"
    />
    <EmptyState
      v-else-if="!identity.proactive.length"
      :icon="Bell"
      title="暂时没有主动消息"
      description="每天的知识回顾、长期目标提醒会在这里出现；也可以点「主动扫描」立即生成一次。"
      min-height="0"
    />
    <ul v-else class="message-list">
      <li
        v-for="message in identity.proactive"
        :key="message.id"
        class="message-item"
        :class="{ unread: message.status === 'unread' }"
      >
        <div class="message-item__head">
          <span class="message-kind">{{ kindLabel(message.kind) }}</span>
          <span class="message-time">{{ formatRelative(message.created_at) }}</span>
          <div class="message-actions">
            <el-button
              v-if="message.status === 'unread'"
              text
              size="small"
              aria-label="标记已读"
              @click="mark(message.id, 'read')"
            >
              <el-icon><Check /></el-icon>
            </el-button>
            <el-button
              text
              size="small"
              aria-label="忽略这条消息"
              @click="mark(message.id, 'dismissed')"
            >
              <el-icon><Close /></el-icon>
            </el-button>
          </div>
        </div>
        <strong class="message-title">{{ message.title }}</strong>
        <p class="message-content">{{ message.content }}</p>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Bell, Check, Close, Refresh } from '@element-plus/icons-vue'
import EmptyState from '../common/EmptyState.vue'
import ErrorState from '../common/ErrorState.vue'
import LoadingState from '../common/LoadingState.vue'
import { useAgentIdentityStore } from '../../stores/agentIdentity'
import { formatRelative } from '../../utils/format'

const identity = useAgentIdentityStore()
const scanning = ref(false)

const kindLabels: Record<string, string> = {
  daily_review: '每日回顾',
  stale_goal: '目标提醒',
}

function kindLabel(kind: string): string {
  return kindLabels[kind] ?? '主动提醒'
}

function reload(): Promise<void> {
  return identity.loadProactive()
}

async function scan(): Promise<void> {
  if (scanning.value) return
  scanning.value = true
  try {
    const result = await identity.scan()
    if (result.created > 0) {
      ElMessage.success(`生成了 ${result.created} 条新提醒`)
    } else {
      ElMessage.info('暂时没有新的提醒')
    }
  } finally {
    scanning.value = false
  }
}

async function mark(id: number, status: 'read' | 'dismissed'): Promise<void> {
  await identity.markRead(id, status)
}
</script>

<style scoped>
.identity-panel {
  display: grid;
  gap: var(--rh-space-base);
  min-height: 200px;
}

.inbox-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--rh-space-sm);
}

.inbox-head strong {
  display: block;
  color: var(--rh-text-primary);
  font-size: var(--rh-fs-md);
}

.inbox-head p {
  margin-top: 4px;
  color: var(--rh-text-tertiary);
  font-size: var(--rh-fs-sm);
}

.message-list {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.message-item {
  padding: 11px 12px;
  border: 1px solid var(--rh-border);
  border-radius: var(--rh-radius-sm);
  background: var(--rh-bg-card);
}

.message-item.unread {
  border-left: 2px solid var(--rh-ai-strong);
}

.message-item__head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.message-kind {
  padding: 2px 7px;
  border-radius: var(--rh-radius-xs);
  background: var(--rh-bg-active);
  color: var(--rh-ai-strong);
  font-size: var(--rh-fs-xs);
  font-weight: 700;
}

.message-time {
  color: var(--rh-text-tertiary);
  font-size: var(--rh-fs-xs);
}

.message-actions {
  display: flex;
  gap: 0;
  margin-left: auto;
}

.message-title {
  display: block;
  margin-top: 8px;
  color: var(--rh-text-primary);
  font-size: var(--rh-fs-md);
}

.message-content {
  margin-top: 5px;
  color: var(--rh-text-secondary);
  font-size: var(--rh-fs-sm);
  line-height: var(--rh-lh-base);
  white-space: pre-wrap;
}
</style>

<template>
  <div class="rh-page ai-page">
    <header class="ai-head">
      <div class="ai-head__text">
        <p class="eyebrow"><span class="eyebrow-mark" aria-hidden="true">✦</span> AI 助手</p>
        <h1>AI 工作台</h1>
        <p class="ai-sub">根据你的笔记回答问题，也可以交给自动助手分步完成一件事。</p>
      </div>
      <div class="ai-head__actions">
        <span class="status-chip" :class="{ 'is-off': status !== null && !status.configured }" :title="indexLabel">
          <span class="status-dot" aria-hidden="true"></span>
          {{ statusText }}
        </span>
        <span v-if="indexLabel" class="index-meta">{{ indexLabel }}</span>
        <span v-if="rebuilding" class="index-meta" role="status">
          正在读取，可能需要几十秒，请先不要关闭页面
        </span>
        <el-button size="small" :loading="rebuilding" @click="rebuildIndex">
          <el-icon v-if="!rebuilding"><Refresh /></el-icon>
          让 AI 重新读取笔记
        </el-button>
        <el-button size="small" text @click="newConversation">新对话</el-button>
      </div>
    </header>

    <div class="mode-switch" role="tablist" aria-label="AI 使用方式">
      <button
        v-for="item in modes"
        :key="item.value"
        role="tab"
        class="mode-tab"
        :class="{ active: mode === item.value }"
        :aria-selected="mode === item.value"
        @click="mode = item.value"
      >
        <el-icon><component :is="item.icon" /></el-icon>
        {{ item.label }}
      </button>
      <p class="mode-hint">{{ modeHint }}</p>
    </div>

    <p v-if="blocked" class="config-notice" role="alert">
      <el-icon><WarningFilled /></el-icon>
      还没有填写 AI 服务密钥，请在项目配置文件中填好后重启服务。
    </p>

    <div class="chat-shell">
      <div ref="scrollRef" class="chat-scroll" @scroll="handleScroll">
        <LoadingState v-if="statusLoading" variant="row" :count="3" label="正在检测 AI 服务" />
        <ErrorState
          v-else-if="statusError"
          title="AI 服务状态加载失败"
          :description="statusError"
          @retry="loadStatus"
        />
        <div v-else-if="!messages.length" class="chat-empty">
          <EmptyState
            :icon="ChatDotRound"
            :title="mode === 'chat' ? '向你的笔记提问' : '交给自动助手一件事'"
            :description="emptyDescription"
            min-height="0"
          >
            <button v-for="item in suggestions" :key="item" class="suggestion" @click="useSuggestion(item)">
              {{ item }}
            </button>
          </EmptyState>
        </div>
        <template v-else>
          <AIMessage
            v-for="item in messages"
            :key="item.id"
            :role="item.role"
            :content="item.content"
            :citations="item.citations"
            :steps="item.steps"
            :streaming="item.streaming"
            :pending="item.pending"
            :error="item.error"
            @confirm="resolvePending(item, true)"
            @reject="resolvePending(item, false)"
          />
        </template>
      </div>

      <div class="composer">
        <textarea
          v-model="input"
          class="composer-input"
          rows="2"
          :disabled="blocked"
          :placeholder="placeholder"
          aria-label="输入问题或任务"
          @keydown="handleKeydown"
          @compositionstart="composing = true"
          @compositionend="composing = false"
        ></textarea>
        <div class="composer-actions">
          <span class="composer-hint">Enter 发送 · Shift + Enter 换行</span>
          <el-button v-if="isStreaming" @click="stop">停止生成</el-button>
          <el-button v-else type="primary" :disabled="blocked || !input.trim()" @click="send">
            发送
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * AI 工作台：根据笔记问答 + 自动助手。
 *
 * 会话状态与流式请求都放在 stores/aiWorkspace 里：页面组件会因切换路由而卸载，
 * 若把请求绑在组件上，用户切走页面时正在生成的回答会被中断。
 * 这里只负责渲染与滚动等界面行为。
 */
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import type { Component } from 'vue'
import { storeToRefs } from 'pinia'
import { ChatDotRound, Cpu, Refresh, WarningFilled } from '@element-plus/icons-vue'
import AIMessage from '../../components/ai/AIMessage.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import ErrorState from '../../components/common/ErrorState.vue'
import LoadingState from '../../components/common/LoadingState.vue'
import { useAIWorkspaceStore } from '../../stores/aiWorkspace'
import type { AIMode, ChatBubble } from '../../stores/aiWorkspace'

const modes: Array<{ value: AIMode; label: string; icon: Component }> = [
  { value: 'chat', label: '笔记问答', icon: ChatDotRound },
  { value: 'agent', label: '自动助手', icon: Cpu },
]

const ai = useAIWorkspaceStore()
const {
  mode,
  messages,
  input,
  status,
  statusLoading,
  statusError,
  blocked,
  statusText,
  indexLabel,
  rebuilding,
  isStreaming,
} = storeToRefs(ai)

const composing = ref(false)
const scrollRef = ref<HTMLElement | null>(null)
const autoScroll = ref(true)

const modeHint = computed(() =>
  mode.value === 'chat'
    ? '回答会标出出自哪篇笔记；找不到依据时会直接告诉你，不会编造'
    : '会修改笔记的操作会先征求你同意，执行过程可以展开查看',
)

const placeholder = computed(() => {
  if (blocked.value) return 'AI 服务还没启用，填写 AI 服务密钥后就能用'
  return mode.value === 'chat'
    ? '向你的笔记提问，例如：总结我关于前端性能的笔记'
    : '说说你想让自动助手做什么，例如：把上周的灵感整理成一篇笔记'
})

const emptyDescription = computed(() =>
  mode.value === 'chat'
    ? '回答都会从你的笔记里找依据，并附上原文段落。'
    : '自动助手可以查找笔记、读取内容、新建或更新笔记；改动笔记前会先请你确认。',
)

const suggestions = computed(() =>
  mode.value === 'chat'
    ? [
        '总结我最近整理的笔记要点',
        '我有哪些关于前端性能的笔记？',
        '把最近三篇笔记串成一条学习路径',
        '根据我的笔记说明怎么做项目答辩',
      ]
    : [
        '找出我关于「前端性能」的三条笔记并给出摘要',
        '把最近的灵感整理成一篇新笔记',
        '按主题梳理我的笔记分类结构',
      ],
)

function handleScroll(): void {
  const el = scrollRef.value
  if (!el) return
  autoScroll.value = el.scrollHeight - el.scrollTop - el.clientHeight < 80
}

function scrollToBottom(): void {
  const el = scrollRef.value
  if (el) el.scrollTop = el.scrollHeight
}

/** 助手内容变化时跟随滚动，用户上滑后不再强制拉回底部 */
const streamTick = computed(() =>
  messages.value
    .map((item) => `${item.content.length}-${item.steps.length}-${item.citations.length}`)
    .join('|'),
)

watch(streamTick, () => {
  if (autoScroll.value) nextTick(scrollToBottom)
})

function loadStatus(): Promise<void> {
  return ai.loadStatus()
}

function rebuildIndex(): Promise<void> {
  return ai.rebuildIndex()
}

async function send(): Promise<void> {
  autoScroll.value = true
  const pending = ai.send()
  await nextTick()
  scrollToBottom()
  await pending
}

function stop(): void {
  ai.stop()
}

function resolvePending(bubble: ChatBubble, approve: boolean): Promise<void> {
  autoScroll.value = true
  const pending = ai.resolvePending(bubble, approve)
  void nextTick(scrollToBottom)
  return pending
}

function newConversation(): void {
  ai.newConversation()
  autoScroll.value = true
}

function useSuggestion(text: string): void {
  input.value = text
  void send()
}

/** Enter 发送、Shift+Enter 换行；输入法组合期间的回车用于选词，不能触发发送 */
function handleKeydown(event: KeyboardEvent): void {
  if (event.key !== 'Enter' || event.shiftKey) return
  if (composing.value || event.isComposing) return
  event.preventDefault()
  void send()
}

onMounted(async () => {
  // 从别的页面切回来时保留原会话，不重复拉状态造成闪烁
  if (!status.value) await ai.loadStatus()
  await nextTick()
  scrollToBottom()
})
</script>

<style scoped>
.ai-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - var(--rh-topbar-height));
  gap: var(--rh-space-base);
}

.ai-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--rh-space-base);
}

.eyebrow {
  margin-bottom: 6px;
  color: var(--rh-text-tertiary);
  font-size: var(--rh-fs-xs);
  font-weight: 700;
  letter-spacing: 0.04em;
}

.eyebrow-mark {
  margin-right: 5px;
  color: var(--rh-ai-strong);
}

.ai-head h1 {
  font-family: var(--rh-font-display);
  font-size: var(--rh-fs-2xl);
  font-weight: 500;
  line-height: var(--rh-lh-tight);
}

.ai-sub {
  margin-top: 6px;
  color: var(--rh-text-secondary);
  font-size: var(--rh-fs-base);
}

.ai-head__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--rh-space-sm);
}

.status-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border: 1px solid var(--rh-border);
  border-radius: var(--rh-radius-xs);
  background: var(--rh-bg-card);
  color: var(--rh-text-secondary);
  font-size: var(--rh-fs-sm);
  font-weight: 600;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--rh-success);
}

.status-chip.is-off .status-dot {
  background: var(--rh-warning);
}

.status-chip.is-off {
  color: var(--rh-warning);
}

.index-meta {
  color: var(--rh-text-tertiary);
  font-size: var(--rh-fs-sm);
}

.mode-switch {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--rh-space-sm);
  padding-bottom: 10px;
  border-bottom: 1px solid var(--rh-border);
}

.mode-tab {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 32px;
  padding: 0 13px;
  border: 1px solid transparent;
  border-radius: var(--rh-radius-xs);
  background: transparent;
  color: var(--rh-text-secondary);
  font-size: var(--rh-fs-md);
  font-weight: 600;
  cursor: pointer;
  transition: var(--rh-transition-all-fast);
}

.mode-tab:hover {
  background: var(--rh-bg-hover);
  color: var(--rh-text-primary);
}

.mode-tab.active {
  border-color: var(--rh-ai-strong);
  background: var(--rh-bg-card);
  color: var(--rh-ai-strong);
}

.mode-hint {
  margin-left: auto;
  color: var(--rh-text-tertiary);
  font-size: var(--rh-fs-sm);
}

.config-notice {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  border: 1px solid var(--rh-warning);
  border-radius: var(--rh-radius-sm);
  background: var(--rh-warning-subtle);
  color: var(--rh-warning);
  font-size: var(--rh-fs-md);
}

.chat-shell {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  border: 1px solid var(--rh-border);
  border-radius: var(--rh-radius-md);
  background: var(--rh-bg-card);
  box-shadow: var(--rh-shadow-sm);
}

.chat-scroll {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: var(--rh-space-lg);
  min-height: 0;
  padding: var(--rh-space-xl);
  overflow-y: auto;
}

.chat-empty {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
}

.suggestion {
  padding: 7px 12px;
  border: 1px dashed var(--rh-border-strong);
  border-radius: var(--rh-radius-xs);
  background: var(--rh-bg-base);
  color: var(--rh-text-secondary);
  font-size: var(--rh-fs-md);
  cursor: pointer;
  transition: var(--rh-transition-all-fast);
}

.suggestion:hover {
  border-color: var(--rh-ai-strong);
  color: var(--rh-text-primary);
  transform: translateY(-1px);
}

.composer {
  padding: var(--rh-space-md) var(--rh-space-base) var(--rh-space-base);
  border-top: 1px solid var(--rh-border-faint);
  background: var(--rh-bg-secondary);
}

.composer-input {
  width: 100%;
  min-height: 58px;
  max-height: 160px;
  padding: 10px 12px;
  border: 1px solid var(--rh-border);
  border-radius: var(--rh-radius-sm);
  background: var(--rh-bg-card);
  color: var(--rh-text-primary);
  font-family: var(--rh-font-sans);
  font-size: var(--rh-fs-base);
  line-height: var(--rh-lh-base);
  resize: none;
  transition: var(--rh-transition-all-fast);
}

.composer-input::placeholder {
  color: var(--rh-text-placeholder);
}

.composer-input:hover {
  border-color: var(--rh-border-strong);
}

.composer-input:focus-visible {
  border-color: var(--rh-primary);
  box-shadow: var(--rh-focus-ring);
}

.composer-input:disabled {
  background: var(--rh-bg-subtle);
  color: var(--rh-text-tertiary);
  cursor: not-allowed;
}

.composer-actions {
  display: flex;
  align-items: center;
  gap: var(--rh-space-sm);
  margin-top: var(--rh-space-sm);
}

.composer-hint {
  color: var(--rh-text-tertiary);
  font-size: var(--rh-fs-xs);
}

.composer-actions .el-button {
  margin-left: auto;
}

@media (max-width: 768px) {
  .ai-page {
    height: calc(100vh - 60px);
    padding: var(--rh-space-base) var(--rh-space-base) var(--rh-space-md);
    gap: var(--rh-space-md);
  }

  .ai-head h1 {
    font-size: var(--rh-fs-xl);
  }

  .ai-head__actions {
    width: 100%;
  }

  .mode-hint {
    width: 100%;
    margin-left: 0;
    order: 3;
  }

  .chat-scroll {
    padding: var(--rh-space-base);
  }

  .composer-hint {
    display: none;
  }
}
</style>

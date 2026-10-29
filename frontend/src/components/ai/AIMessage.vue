<template>
  <article class="ai-message" :class="`is-${role}`">
    <!-- 用户消息：纯文本展示，避免把用户输入当 Markdown 解析 -->
    <div v-if="role === 'user'" class="user-bubble">{{ content }}</div>

    <div v-else class="assistant-body">
      <div class="assistant-head">
        <span class="ai-mark" aria-hidden="true">✦</span>
        <span class="assistant-label">ResourceHub AI</span>
        <span v-if="streaming" class="typing" role="status" aria-label="正在生成回答">
          <i></i><i></i><i></i>
        </span>
      </div>

      <div v-if="content" class="rh-markdown ai-markdown" aria-live="polite" v-html="renderedHtml"></div>
      <p v-else-if="streaming" class="thinking">正在阅读你的笔记…</p>

      <!-- 检索引用：点击展开片段，不跳转页面（笔记库暂不支持按 id 直达） -->
      <div v-if="citations.length" class="citations">
        <span class="citations-label">引用 {{ citations.length }} 段原文</span>
        <button
          v-for="item in citations"
          :key="`${item.chunk_id}-${item.index}`"
          class="citation-chip"
          :class="{ open: activeCitationId === item.chunk_id }"
          :aria-expanded="activeCitationId === item.chunk_id"
          :aria-label="`查看引用段落：${item.note_title}`"
          @click="toggleCitation(item.chunk_id)"
        >
          <span class="citation-index">{{ item.index }}</span>
          <span class="citation-title">{{ item.note_title }}</span>
        </button>
        <p v-if="activeCitation" class="citation-snippet">
          {{ activeCitation.snippet }}
          <span class="citation-score">匹配度 {{ Math.round(activeCitation.score * 100) }}%</span>
        </p>
      </div>

      <!-- Agent 执行轨迹：默认折叠，避免遮挡结论 -->
      <details v-if="steps.length" class="agent-steps">
        <summary>执行过程 · {{ steps.length }} 步</summary>
        <ol class="step-list">
          <li v-for="(step, index) in steps" :key="`${step.step}-${step.name}-${index}`" class="step-item">
            <div class="step-head">
              <span class="step-no">{{ String(step.step).padStart(2, '0') }}</span>
              <strong>{{ toolLabel(step.name) }}</strong>
              <span v-if="step.result === undefined" class="step-pending">执行中</span>
              <span v-else class="step-done">已完成</span>
            </div>
            <pre v-if="step.arguments && step.arguments !== '{}'" class="step-block">{{ prettyJson(step.arguments) }}</pre>
            <pre v-if="step.result" class="step-block step-block--result">{{ step.result }}</pre>
          </li>
        </ol>
      </details>

      <!-- 写操作人在环确认 -->
      <div v-if="pending" class="confirm-card" role="group" aria-label="等待你确认的操作">
        <p class="confirm-title">{{ pending.message }}</p>
        <p class="confirm-tool">
          <el-icon><WarningFilled /></el-icon>
          将要执行：{{ toolLabel(pending.tool) }}
        </p>
        <pre v-if="pending.arguments && pending.arguments !== '{}'" class="step-block">{{ prettyJson(pending.arguments) }}</pre>
        <div class="confirm-actions">
          <el-button size="small" type="primary" @click="emit('confirm')">同意执行</el-button>
          <el-button size="small" @click="emit('reject')">取消</el-button>
        </div>
      </div>

      <p v-if="error" class="msg-error" role="alert">{{ error }}</p>
    </div>
  </article>
</template>

<script setup lang="ts">
/**
 * AI 消息气泡：用户消息纯文本、助手消息走 Markdown 管线（markdown-it + DOMPurify）。
 * 同时承载引用、Agent 执行轨迹与写操作确认卡。
 */
import { computed, onUnmounted, ref, watch } from 'vue'
import { WarningFilled } from '@element-plus/icons-vue'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'
import type { AgentStep, AwaitingConfirmation, Citation } from '../../api/ai'

const props = withDefaults(
  defineProps<{
    role: 'user' | 'assistant'
    content: string
    citations?: Citation[]
    steps?: AgentStep[]
    streaming?: boolean
    pending?: AwaitingConfirmation | null
    error?: string | null
  }>(),
  {
    citations: () => [],
    steps: () => [],
    streaming: false,
    pending: null,
    error: null,
  },
)

const emit = defineEmits<{ confirm: []; reject: [] }>()

const md = new MarkdownIt({ html: false, linkify: true, breaks: true })

/** 流式内容按帧节流，避免每个 token 都触发一次 Markdown 重新解析 */
const displayContent = ref(props.content)
let frameId = 0

watch(
  () => props.content,
  (value) => {
    if (!props.streaming) {
      displayContent.value = value
      return
    }
    if (frameId) return
    frameId = requestAnimationFrame(() => {
      frameId = 0
      displayContent.value = props.content
    })
  },
)

onUnmounted(() => {
  if (frameId) cancelAnimationFrame(frameId)
})

const renderedHtml = computed(() => DOMPurify.sanitize(md.render(displayContent.value)))

/** 当前展开的引用片段，同一时间只展开一条 */
const activeCitationId = ref<number | null>(null)

const activeCitation = computed(
  () => props.citations.find((item) => item.chunk_id === activeCitationId.value) || null,
)

function toggleCitation(chunkId: number): void {
  activeCitationId.value = activeCitationId.value === chunkId ? null : chunkId
}

const TOOL_LABELS: Record<string, string> = {
  search_notes: '查找笔记',
  read_note: '读取笔记',
  list_categories: '列出分类',
  search_prompts: '查找提示词',
  create_note: '新建笔记',
  update_note: '更新笔记',
}

/** 工具名转中文；未知工具原样展示 */
function toolLabel(name: string): string {
  return TOOL_LABELS[name] || name
}

/** 工具参数是 JSON 字符串，格式化后便于阅读 */
function prettyJson(raw: string): string {
  try {
    return JSON.stringify(JSON.parse(raw), null, 2)
  } catch {
    return raw
  }
}
</script>

<style scoped>
.ai-message {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ai-message.is-user {
  align-items: flex-end;
}

.user-bubble {
  max-width: min(78%, 640px);
  padding: 11px 15px;
  border-radius: var(--rh-radius-md) var(--rh-radius-md) var(--rh-radius-xs) var(--rh-radius-md);
  background: var(--rh-primary);
  color: var(--rh-on-primary);
  font-size: var(--rh-fs-body);
  line-height: var(--rh-lh-base);
  white-space: pre-wrap;
  word-break: break-word;
}

.assistant-body {
  width: 100%;
  max-width: 860px;
}

.assistant-head {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 8px;
  color: var(--rh-text-tertiary);
  font-size: var(--rh-fs-sm);
  font-weight: 700;
}

.ai-mark {
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--rh-ai);
  color: var(--rh-on-ai);
  font-size: 11px;
}

.assistant-label {
  letter-spacing: 0.02em;
}

.typing {
  display: inline-flex;
  gap: 3px;
  margin-left: 2px;
}

.typing i {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--rh-text-tertiary);
  animation: typingPulse 1.1s ease-in-out infinite;
}

.typing i:nth-child(2) {
  animation-delay: 0.15s;
}

.typing i:nth-child(3) {
  animation-delay: 0.3s;
}

@keyframes typingPulse {
  0%,
  60%,
  100% {
    opacity: 0.28;
    transform: translateY(0);
  }
  30% {
    opacity: 1;
    transform: translateY(-2px);
  }
}

.thinking {
  color: var(--rh-text-tertiary);
  font-size: var(--rh-fs-base);
}

.ai-markdown {
  padding: 2px 4px;
  font-size: var(--rh-fs-body);
  line-height: var(--rh-lh-relaxed);
  word-break: break-word;
}

.citations {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
}

.citations-label {
  color: var(--rh-text-tertiary);
  font-size: var(--rh-fs-sm);
  font-weight: 700;
}

.citation-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 240px;
  padding: 3px 9px 3px 4px;
  border: 1px solid var(--rh-border);
  border-radius: var(--rh-radius-xs);
  background: var(--rh-bg-card);
  color: var(--rh-text-secondary);
  font-size: var(--rh-fs-sm);
  cursor: pointer;
  transition: var(--rh-transition-all-fast);
}

.citation-chip:hover,
.citation-chip.open {
  border-color: var(--rh-ai-strong);
  color: var(--rh-text-primary);
}

.citation-index {
  display: grid;
  place-items: center;
  min-width: 17px;
  height: 17px;
  padding: 0 4px;
  border-radius: var(--rh-radius-xs);
  background: var(--rh-ai);
  color: var(--rh-on-ai);
  font-size: var(--rh-fs-xs);
  font-weight: 800;
}

.citation-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.citation-snippet {
  width: 100%;
  margin-top: 4px;
  padding: 10px 12px;
  border-left: 2px solid var(--rh-ai);
  border-radius: var(--rh-radius-xs);
  background: var(--rh-bg-inset);
  color: var(--rh-text-secondary);
  font-size: var(--rh-fs-md);
  line-height: var(--rh-lh-base);
}

.citation-score {
  display: block;
  margin-top: 6px;
  color: var(--rh-text-tertiary);
  font-size: var(--rh-fs-xs);
}

.agent-steps {
  margin-top: 10px;
  border-radius: var(--rh-radius-sm);
  background: var(--rh-bg-secondary);
}

.agent-steps summary {
  padding: 9px 12px;
  color: var(--rh-text-secondary);
  font-size: var(--rh-fs-md);
  font-weight: 700;
  cursor: pointer;
}

.step-list {
  display: grid;
  gap: 8px;
  padding: 0 12px 12px;
  list-style: none;
}

.step-item {
  padding: 9px 11px;
  border-radius: var(--rh-radius-xs);
  background: var(--rh-bg-card);
}

.step-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--rh-fs-md);
}

.step-no {
  color: var(--rh-text-tertiary);
  font-family: var(--rh-font-mono);
  font-size: var(--rh-fs-xs);
}

.step-head strong {
  color: var(--rh-text-primary);
}

.step-pending {
  margin-left: auto;
  color: var(--rh-ai-strong);
  font-size: var(--rh-fs-xs);
  font-weight: 700;
}

.step-done {
  margin-left: auto;
  color: var(--rh-success-strong);
  font-size: var(--rh-fs-xs);
  font-weight: 700;
}

.step-block {
  margin-top: 6px;
  padding: 8px 10px;
  overflow-x: auto;
  border-radius: var(--rh-radius-xs);
  background: var(--rh-code-bg);
  color: var(--rh-code-text);
  font-family: var(--rh-font-mono);
  font-size: var(--rh-fs-sm);
  line-height: var(--rh-lh-tight);
  white-space: pre-wrap;
  word-break: break-word;
}

.step-block--result {
  max-height: 180px;
  overflow-y: auto;
  background: var(--rh-bg-inset);
  color: var(--rh-text-secondary);
}

.confirm-card {
  margin-top: 10px;
  padding: 12px 14px;
  border-radius: var(--rh-radius-sm);
  background: var(--rh-bg-elevated);
}

.confirm-title {
  color: var(--rh-text-primary);
  font-size: var(--rh-fs-base);
  font-weight: 700;
}

.confirm-tool {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
  color: var(--rh-warning);
  font-size: var(--rh-fs-md);
}

.confirm-actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.msg-error {
  margin-top: 8px;
  padding: 8px 11px;
  border-radius: var(--rh-radius-xs);
  background: var(--rh-danger-subtle);
  color: var(--rh-danger);
  font-size: var(--rh-fs-md);
}

@media (max-width: 768px) {
  .user-bubble {
    max-width: 92%;
  }

  .ai-markdown {
    padding: 12px;
  }
}
</style>

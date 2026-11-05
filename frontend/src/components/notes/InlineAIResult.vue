<template>
  <teleport to="body">
    <div
      v-if="visible"
      class="inline-ai-result"
      role="dialog"
      aria-label="内联 AI 结果"
      :style="cardStyle"
      @mousedown.stop
    >
      <div class="result-header">
        <span class="result-title">{{ actionLabel }}</span>
        <button type="button" class="result-close" aria-label="关闭结果卡片" @click="emit('close')">×</button>
      </div>

      <div class="result-body">
        <LoadingState v-if="loading" variant="detail" label="AI 正在处理" />

        <div v-else-if="error" class="result-error" role="alert">
          <p>{{ error }}</p>
          <button type="button" class="result-btn" @click="emit('retry')">重试</button>
        </div>

        <EmptyState
          v-else-if="!result"
          title="AI 没有返回内容"
          description="可以点击重试再试一次"
          min-height="120px"
        />

        <div v-else class="rh-markdown result-content" v-html="renderedHtml"></div>
      </div>

      <div v-if="!loading && !error && result" class="result-footer">
        <button type="button" class="result-btn is-primary" @click="emit('insert')">
          {{ action === 'rewrite' ? '替换原文' : '插入到下方' }}
        </button>
        <button type="button" class="result-btn" @click="copyResult">复制</button>
        <button type="button" class="result-btn" @click="emit('retry')">重试</button>
      </div>
    </div>
  </teleport>
</template>

<script setup lang="ts">
import { computed, onUnmounted } from 'vue'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'
import { ElMessage } from 'element-plus'
import type { InlineActionName } from '../../api/ai'
import LoadingState from '../common/LoadingState.vue'
import EmptyState from '../common/EmptyState.vue'

const props = defineProps<{
  visible: boolean
  action: InlineActionName
  loading: boolean
  result: string
  error: string
  rect: { top: number; left: number; bottom: number }
}>()

const emit = defineEmits<{
  insert: []
  retry: []
  close: []
}>()

const md = new MarkdownIt({ html: false })

const actionLabel = computed(
  () => ({ explain: 'AI 解释', rewrite: 'AI 改写', ask: 'AI 回答' })[props.action],
)

/** AI 输出的 Markdown 转 HTML 并消毒后才渲染 / 插入 */
const renderedHtml = computed(() => DOMPurify.sanitize(md.render(props.result || '')))

// 卡片放在选区下方；底部空间不足时向上翻转并限制高度
const CARD_WIDTH = 420
const CARD_MAX_HEIGHT = 360

const cardStyle = computed(() => {
  const below = props.rect.bottom + 8
  const overflow = below + CARD_MAX_HEIGHT > window.innerHeight - 8
  return {
    left: `${Math.min(Math.max(8, props.rect.left), window.innerWidth - CARD_WIDTH - 8)}px`,
    top: `${overflow ? Math.max(8, props.rect.top - CARD_MAX_HEIGHT - 8) : below}px`,
    width: `${CARD_WIDTH}px`,
  }
})

async function copyResult() {
  try {
    await navigator.clipboard.writeText(props.result)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败，请手动选择文本复制')
  }
}

// Esc 关闭结果卡片
function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && props.visible) emit('close')
}

document.addEventListener('keydown', handleKeydown)
onUnmounted(() => document.removeEventListener('keydown', handleKeydown))
</script>

<style scoped>
.inline-ai-result {
  position: fixed;
  z-index: var(--rh-z-popover);
  display: flex;
  flex-direction: column;
  max-height: 360px;
  background: var(--rh-bg-card);
  border: 1px solid var(--rh-ai-strong);
  border-radius: var(--rh-radius-sm);
  box-shadow: var(--rh-shadow-lg);
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid var(--rh-border-faint);
}

.result-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--rh-ai-strong);
}

.result-close {
  border: none;
  background: transparent;
  color: var(--rh-text-tertiary);
  font-size: 15px;
  line-height: 1;
  padding: 2px 6px;
  cursor: pointer;
  border-radius: var(--rh-radius-xs);
}

.result-close:hover {
  background: var(--rh-bg-hover);
  color: var(--rh-text-primary);
}

.result-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.result-content {
  font-size: 13.5px;
}

.result-error {
  font-size: 13px;
  color: var(--rh-danger);
}

.result-error .result-btn {
  margin-top: 8px;
}

.result-footer {
  display: flex;
  gap: 6px;
  padding: 8px 12px;
  border-top: 1px solid var(--rh-border-faint);
}

.result-btn {
  border: 1px solid var(--rh-border);
  background: var(--rh-bg-card);
  color: var(--rh-text-primary);
  font-size: 12px;
  padding: 4px 12px;
  border-radius: var(--rh-radius-xs);
  cursor: pointer;
  transition: background-color var(--rh-duration-fast) var(--rh-transition-fast);
}

.result-btn:hover {
  background: var(--rh-bg-hover);
}

.result-btn.is-primary {
  background: var(--rh-ai);
  border-color: var(--rh-ai);
  color: var(--rh-on-ai);
  font-weight: 600;
}

.result-btn.is-primary:hover {
  background: var(--rh-ai-strong);
}
</style>

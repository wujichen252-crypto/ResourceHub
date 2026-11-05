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
        <TrustBadge v-if="trust" :trust="trust" />
      </div>

      <!-- 正文：渲染后把 [n] 后处理为可交互上标（见 decorateCitations） -->
      <div
        v-if="content"
        ref="bodyRef"
        class="rh-markdown ai-markdown"
        aria-live="polite"
        v-html="renderedHtml"
        @click="handleBodyClick"
        @mouseover="handleRefHover"
        @mouseleave="clearRefHover"
        @keydown="handleRefKeydown"
      ></div>
      <p v-else-if="streaming" class="thinking">正在阅读你的笔记…</p>

      <!-- 检索引用：点击展开片段并与正文上标双向高亮（笔记库暂不支持按 id 直达） -->
      <div v-if="citations.length" class="citations">
        <span class="citations-label">引用 {{ citations.length }} 段原文</span>
        <button
          v-for="item in citations"
          :key="`${item.chunk_id}-${item.index}`"
          class="citation-chip"
          :class="{ open: activeCitationId === item.chunk_id, linked: hoveredChipIndex === item.index }"
          :aria-expanded="activeCitationId === item.chunk_id"
          :aria-label="`查看引用段落：${item.note_title}`"
          @click="toggleCitation(item)"
          @mouseenter="hoveredChipIndex = item.index"
          @mouseleave="hoveredChipIndex = null"
        >
          <span class="citation-index">{{ item.index }}</span>
          <span class="citation-title">{{ item.note_title }}</span>
        </button>
        <p v-if="activeCitation" class="citation-snippet">
          <template v-if="snippetSegments">
            <span
              v-for="(seg, segIndex) in snippetSegments"
              :key="segIndex"
              :class="{ 'snippet-hl': seg.hl }"
            >{{ seg.text }}</span>
          </template>
          <template v-else>{{ activeCitation.snippet }}</template>
          <!-- vector_score 才是语义相似度（cosine 0~1）；RRF 排序分太小不适合展示成百分比 -->
          <span class="citation-score">
            <template v-if="activeCitation.vector_score > 0">
              语义相关度 {{ Math.round(activeCitation.vector_score * 100) }}%
            </template>
            <template v-else>BM25 关键词命中（向量检索不可用）</template>
          </span>
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
 * 同时承载可信度徽章、可交互引用上标（双向联动 + 支撑句高亮）、Agent 执行轨迹与写操作确认卡。
 */
import { computed, nextTick, onUnmounted, ref, watch } from 'vue'
import { WarningFilled } from '@element-plus/icons-vue'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'
import TrustBadge from './TrustBadge.vue'
import type { AgentStep, AwaitingConfirmation, Citation, TrustReport } from '../../api/ai'

const props = withDefaults(
  defineProps<{
    role: 'user' | 'assistant'
    content: string
    citations?: Citation[]
    steps?: AgentStep[]
    streaming?: boolean
    pending?: AwaitingConfirmation | null
    error?: string | null
    trust?: TrustReport | null
  }>(),
  {
    citations: () => [],
    steps: () => [],
    streaming: false,
    pending: null,
    error: null,
    trust: null,
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

/** 触发展开的上标所在回答句，用于片段内支撑句高亮；点 chip 展开时为空 */
const activeSentence = ref('')

/** chip 悬停时的编号，用于反向点亮正文中的对应上标 */
const hoveredChipIndex = ref<number | null>(null)

/** chip 点击后的脉冲编号（短暂点亮正文上标） */
const pulseIndex = ref<number | null>(null)

let pulseTimer: number | undefined

const activeCitation = computed(
  () => props.citations.find((item) => item.chunk_id === activeCitationId.value) || null,
)

function toggleCitation(item: Citation): void {
  if (activeCitationId.value === item.chunk_id) {
    activeCitationId.value = null
    activeSentence.value = ''
  } else {
    activeCitationId.value = item.chunk_id
    activeSentence.value = ''
    // 点 chip 反向脉冲正文上标，提示「这一条用在了哪」
    pulseIndex.value = item.index
    if (pulseTimer !== undefined) window.clearTimeout(pulseTimer)
    pulseTimer = window.setTimeout(() => {
      pulseIndex.value = null
    }, 1300)
  }
  applyRefStates()
}

// ── 引用上标后处理与双向联动 ────────────────────────────────────

const bodyRef = ref<HTMLElement | null>(null)

const CITE_PATTERN = /\[(\d+)\]/g

/**
 * 把渲染后 HTML 文本节点中的 [n] 替换为可交互上标。
 * 跳过代码块与已处理节点；流式期间 innerHTML 随 displayContent 重建，每次全量重跑。
 */
function decorateCitations(): void {
  const root = bodyRef.value
  if (!root) return
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  const targets: Array<{ node: Text; matches: RegExpMatchArray[] }> = []
  let node = walker.nextNode()
  while (node) {
    const textNode = node as Text
    node = walker.nextNode()
    const parent = textNode.parentElement
    if (!parent || parent.closest('pre, code, sup.rh-cite-ref')) continue
    const text = textNode.textContent ?? ''
    CITE_PATTERN.lastIndex = 0
    if (!CITE_PATTERN.test(text)) continue
    CITE_PATTERN.lastIndex = 0
    targets.push({ node: textNode, matches: [...text.matchAll(CITE_PATTERN)] })
  }
  for (const target of targets) replaceWithCitationRefs(target.node, target.matches)
  applyRefStates()
}

function replaceWithCitationRefs(node: Text, matches: RegExpMatchArray[]): void {
  const text = node.textContent ?? ''
  const fragment = document.createDocumentFragment()
  let cursor = 0
  for (const match of matches) {
    const start = match.index ?? 0
    if (start > cursor) fragment.appendChild(document.createTextNode(text.slice(cursor, start)))
    const sup = document.createElement('sup')
    sup.className = 'rh-cite-ref'
    sup.dataset.cite = match[1]
    sup.setAttribute('role', 'button')
    sup.setAttribute('tabindex', '0')
    sup.setAttribute('aria-label', `查看引用来源 ${match[1]}`)
    sup.textContent = match[1]
    fragment.appendChild(sup)
    cursor = start + match[0].length
  }
  if (cursor < text.length) fragment.appendChild(document.createTextNode(text.slice(cursor)))
  node.replaceWith(fragment)
}

/** 按 hover / 脉冲 / 展开状态给上标加高亮类 */
function applyRefStates(): void {
  const root = bodyRef.value
  if (!root) return
  const linked = hoveredChipIndex.value
  const pulse = pulseIndex.value
  root.querySelectorAll<HTMLElement>('sup.rh-cite-ref').forEach((el) => {
    const cite = Number(el.dataset.cite)
    el.classList.toggle('is-linked', linked !== null && cite === linked)
    el.classList.toggle('is-pulse', pulse !== null && cite === pulse)
  })
}

/** 点击/回车正文上标：展开对应引用片段，并记录所在句子用于支撑句高亮 */
function activateRef(sup: HTMLElement): void {
  const cite = Number(sup.dataset.cite)
  const citation = props.citations.find((item) => item.index === cite)
  if (!citation) return
  activeCitationId.value = activeCitationId.value === citation.chunk_id ? null : citation.chunk_id
  activeSentence.value = activeCitationId.value === null ? '' : findSentenceAt(sup)
}

/** 计算上标所在的回答句子（按块级元素文本 + 上标偏移定位） */
function findSentenceAt(sup: HTMLElement): string {
  const block = sup.closest('p, li, blockquote, h1, h2, h3, h4, td')
  if (!block) return ''
  const full = block.textContent ?? ''
  let offset = 0
  const walker = document.createTreeWalker(block, NodeFilter.SHOW_TEXT)
  let node = walker.nextNode() as Text | null
  while (node) {
    if (node.parentElement === sup) break
    offset += (node.textContent ?? '').length
    node = walker.nextNode() as Text | null
  }
  for (const match of full.matchAll(/[^。！？!?\n]*[。！？!?\n]?/g)) {
    const start = match.index ?? 0
    const end = start + match[0].length
    if (offset >= start && offset < end) return match[0].trim()
  }
  return ''
}

function handleBodyClick(event: MouseEvent): void {
  const sup = (event.target as HTMLElement).closest<HTMLElement>('sup.rh-cite-ref')
  if (!sup) return
  activateRef(sup)
  applyRefStates()
}

function handleRefKeydown(event: KeyboardEvent): void {
  if (event.key !== 'Enter' && event.key !== ' ') return
  const sup = (event.target as HTMLElement).closest<HTMLElement>('sup.rh-cite-ref')
  if (!sup) return
  event.preventDefault()
  activateRef(sup)
  applyRefStates()
}

/** 悬停正文上标：反向点亮对应引用 chip */
function handleRefHover(event: MouseEvent): void {
  const sup = (event.target as HTMLElement).closest<HTMLElement>('sup.rh-cite-ref')
  const cite = sup ? Number(sup.dataset.cite) : null
  hoveredChipIndex.value = cite !== null && !Number.isNaN(cite) ? cite : null
}

function clearRefHover(): void {
  hoveredChipIndex.value = null
}

// ── 片段内支撑句高亮 ────────────────────────────────────────────

interface SnippetSegment {
  text: string
  hl: boolean
}

/** 支撑句判定的相似度阈值：低于它不强标，诚实呈现「依据是整段」 */
const SUPPORT_SIMILARITY_THRESHOLD = 0.35

function charBigrams(text: string): Set<string> {
  const cleaned = text.replace(/\s+/g, '')
  const grams = new Set<string>()
  for (let i = 0; i < cleaned.length - 1; i += 1) grams.add(cleaned.slice(i, i + 2))
  return grams
}

/** 字符 bigram Dice 相似度（中英混合精简版，对标 retrieval.tokenize 思路） */
function bigramSimilarity(a: string, b: string): number {
  const gramsA = charBigrams(a)
  const gramsB = charBigrams(b)
  if (!gramsA.size || !gramsB.size) return 0
  let intersection = 0
  for (const gram of gramsA) if (gramsB.has(gram)) intersection += 1
  return (2 * intersection) / (gramsA.size + gramsB.size)
}

/**
 * 展开片段的渲染分段：与触发回答句最相似的片段句加高亮。
 * 无触发句（点 chip 展开）或相似度不足时返回 null，整段原样展示。
 */
const snippetSegments = computed<Array<SnippetSegment> | null>(() => {
  const citation = activeCitation.value
  if (!citation || !activeSentence.value) return null
  const pattern = /[^。！？!?\n]*[。！？!?\n]?/g
  const parts = [...citation.snippet.matchAll(pattern)]
    .map((match) => match[0])
    .filter((part) => part.trim())
  if (!parts.length) return null
  let bestIndex = -1
  let bestScore = 0
  parts.forEach((part, index) => {
    const score = bigramSimilarity(activeSentence.value, part)
    if (score > bestScore) {
      bestScore = score
      bestIndex = index
    }
  })
  if (bestIndex < 0 || bestScore < SUPPORT_SIMILARITY_THRESHOLD) return null
  // 按原文位置重组，保留分隔标点：命中段整体替换
  const segments: Array<SnippetSegment> = []
  const full = citation.snippet
  let cursor = 0
  parts.forEach((part, index) => {
    const start = full.indexOf(part, cursor)
    if (start < 0) return
    if (start > cursor) segments.push({ text: full.slice(cursor, start), hl: false })
    segments.push({ text: part, hl: index === bestIndex })
    cursor = start + part.length
  })
  if (cursor < full.length) segments.push({ text: full.slice(cursor), hl: false })
  return segments
})

// 内容变化（流式增量 / 非流式赋值）后重建上标；innerHTML 已被 Vue 重写
watch(displayContent, () => {
  void nextTick(decorateCitations)
})
watch([hoveredChipIndex, pulseIndex], () => {
  void nextTick(applyRefStates)
})

onUnmounted(() => {
  if (frameId) cancelAnimationFrame(frameId)
  if (pulseTimer !== undefined) window.clearTimeout(pulseTimer)
})

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

.citation-chip.linked {
  border-color: var(--rh-ai-strong);
  background: var(--rh-ai-subtle);
}

/* ── 引用上标（正文 [n] → 可交互 sup） ─────────────────────── */
.ai-markdown :deep(sup.rh-cite-ref) {
  margin: 0 1px;
  padding: 0 5px;
  border-radius: 999px;
  background: var(--rh-ai-subtle);
  color: var(--rh-ai-strong);
  font-size: var(--rh-fs-xs);
  font-weight: 700;
  line-height: 1.5;
  cursor: pointer;
  transition: var(--rh-transition-all-fast);
}

.ai-markdown :deep(sup.rh-cite-ref:hover),
.ai-markdown :deep(sup.rh-cite-ref.is-linked) {
  background: var(--rh-ai);
  color: var(--rh-on-ai);
}

.ai-markdown :deep(sup.rh-cite-ref.is-pulse) {
  animation: citePulse 0.6s ease-in-out 2;
}

@keyframes citePulse {
  0%,
  100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.25);
  }
}

@media (prefers-reduced-motion: reduce) {
  .ai-markdown :deep(sup.rh-cite-ref.is-pulse) {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
  }
}

/* ── 片段内支撑句高亮 ─────────────────────────────────────── */
.citation-snippet :deep(.snippet-hl),
.citation-snippet .snippet-hl {
  padding: 1px 2px;
  border-radius: var(--rh-radius-xs);
  background: var(--rh-ai-subtle);
  color: var(--rh-text-primary);
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

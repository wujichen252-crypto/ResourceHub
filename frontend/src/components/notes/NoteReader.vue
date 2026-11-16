<template>
  <div class="note-reader">
    <div class="reader-header">
      <el-button text @click="$emit('back')">
        <el-icon><ArrowLeft /></el-icon> 返回目录
      </el-button>
      <div class="reader-actions">
        <el-button size="small" @click="handleTogglePin">
          <el-icon><Top /></el-icon>
          {{ note.is_pinned ? '取消置顶' : '置顶' }}
        </el-button>
        <el-button
          size="small"
          :type="note.visibility === 'public' ? 'warning' : 'success'"
          :loading="publishing"
          @click="$emit('togglePublish')"
        >
          <el-icon><Promotion /></el-icon>
          {{ note.visibility === 'public' ? '取消发布' : '发布到广场' }}
        </el-button>
        <el-button size="small" type="primary" @click="$emit('edit')">
          <el-icon><Edit /></el-icon> 编辑
        </el-button>
        <el-button size="small" type="danger" @click="handleDelete">
          <el-icon><Delete /></el-icon> 删除
        </el-button>
      </div>
    </div>

    <div class="reader-body" @click="handleContentClick">
      <h1 class="note-title">{{ note.title }}</h1>

      <div class="note-metadata">
        <span v-if="note.is_pinned" class="meta-item">
          <el-tag size="small" type="warning">📌 置顶</el-tag>
        </span>
        <span v-if="note.category_name" class="meta-item">
          <el-tag size="small">{{ note.category_name }}</el-tag>
        </span>
        <span class="meta-item">更新: {{ formatTime(note.updated_at) }}</span>
        <span class="meta-item">创建: {{ formatTime(note.created_at) }}</span>
      </div>

      <div v-if="note.tags?.length" class="note-tags">
        <el-tag v-for="tag in note.tags" :key="tag" size="small" type="info">{{ tag }}</el-tag>
      </div>

      <el-divider />

      <div class="note-content rh-markdown" v-html="sanitizedContent" />

      <!-- 反向链接面板：无引用时不渲染，避免占位噪声 -->
      <section v-if="backlinks.length" class="backlinks-panel" aria-label="链接到此笔记">
        <h2 class="backlinks-title">链接到此笔记 · {{ backlinks.length }}</h2>
        <div class="backlinks-list">
          <button
            v-for="item in backlinks"
            :key="item.id"
            type="button"
            class="backlink-item"
            :aria-label="`打开「${item.title}」`"
            @click.stop="emitOpen({ noteId: item.id, title: item.title })"
          >
            <el-icon><Link /></el-icon>
            <span class="backlink-main">
              <span class="backlink-title">{{ item.title }}</span>
              <span v-if="item.context" class="backlink-context">{{ item.context }}</span>
            </span>
            <span class="backlink-time">{{ formatRelative(item.updated_at) }}</span>
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ArrowLeft, Top, Edit, Delete, Promotion, Link } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'
import { notesApi, type Note, type NoteBacklink } from '../../api/notes'
import { formatDateTime, formatRelative } from '../../utils/format'

const md = new MarkdownIt({ html: false, linkify: true, typographer: true })

const props = defineProps<{
  note: Note
  publishing?: boolean
}>()

const emit = defineEmits<{
  back: []
  edit: []
  'delete': [id: number]
  'togglePin': [id: number]
  togglePublish: []
  /** 点击正文链接 chip 或反向链接：noteId 为空表示死链，由外层提供解析/创建流程 */
  'open-note': [payload: { noteId: number | null; title: string }]
}>()

function isHtml(str: string): boolean {
  return /<[a-z][\s\S]*>/i.test(str)
}

// markdown 轨的 [[标题]] 在渲染后转换为链接 chip；json 轨的 HTML 快照已自带 chip
const WIKILINK_HTML = /\[\[([^\[\]]+?)\]\]/g
function escapeHtmlText(s: string): string {
  return s.replace(/[&<>"']/g, (ch) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch] ?? ch
  ))
}

const sanitizedContent = computed(() => {
  const raw = props.note.content || ''
  const html = isHtml(raw) ? raw : md.render(raw)
  const safe = DOMPurify.sanitize(html)
  if (props.note.content_format === 'json') return safe
  // markdown 轨：把纯文本 wikilink 转成 chip（DOMPurify 之后替换，内容为生成态、无注入风险）
  return safe.replace(
    WIKILINK_HTML,
    (_, title: string) =>
      `<span data-type="noteLink" class="note-wikilink is-dead" data-note-title="${escapeHtmlText(title.trim())}">${escapeHtmlText(title.trim())}</span>`,
  )
})

// ── 反向链接 ──
const backlinks = ref<NoteBacklink[]>([])

watch(
  () => props.note.id,
  async (noteId) => {
    backlinks.value = []
    if (!noteId) return
    try {
      const data = await notesApi.backlinks(noteId)
      // 响应返回时若已切到另一篇笔记，丢弃过期结果
      if (props.note.id === noteId) backlinks.value = data.items
    } catch {
      // 反链加载失败不打断阅读
    }
  },
  { immediate: true },
)

function emitOpen(payload: { noteId: number | null; title: string }) {
  emit('open-note', payload)
}

/** 正文链接 chip 点击委托 */
function handleContentClick(event: MouseEvent) {
  const target = event.target as HTMLElement | null
  const chip = target?.closest?.('[data-type="noteLink"]') as HTMLElement | null
  if (!chip) return
  const noteIdRaw = chip.getAttribute('data-note-id')
  emitOpen({
    noteId: noteIdRaw ? Number(noteIdRaw) : null,
    title: chip.getAttribute('data-note-title') || '',
  })
}

function formatTime(dateStr: string) {
  return formatDateTime(dateStr)
}

function handleTogglePin() {
  emit('togglePin', props.note.id)
}

async function handleDelete() {
  try {
    await ElMessageBox.confirm(
      '确定要删除这篇笔记吗？此操作不可恢复。',
      '确认删除',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' },
    )
    emit('delete', props.note.id)
  } catch {
    // cancelled
  }
}
</script>

<style scoped>
.note-reader {
  max-width: 860px;
  margin: 0 auto;
  padding: var(--rh-page-pad);
}

.reader-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 8px;
}

.reader-actions {
  display: flex;
  gap: 8px;
}

.reader-body {
  padding: 8px 0;
}

.note-title {
  font-family: var(--rh-font-display);
  font-size: 30px;
  font-weight: 700;
  color: var(--rh-text-primary);
  margin-bottom: 20px;
  line-height: 1.35;
  letter-spacing: -0.02em;
}

.note-metadata {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
  margin-bottom: 12px;
}

.meta-item {
  font-size: 13px;
  color: var(--rh-text-tertiary);
}

.note-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.note-content {
  font-size: 15.5px;
  line-height: 1.85;
  color: var(--rh-text-primary);
}

/* ── 反向链接面板 ── */
.backlinks-panel {
  margin-top: 40px;
  padding-top: 20px;
  border-top: 1px solid var(--rh-border-light);
}

.backlinks-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--rh-text-tertiary);
  letter-spacing: 0.02em;
  margin-bottom: 12px;
}

.backlinks-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.backlink-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 10px;
  border: 1px solid var(--rh-border-faint);
  border-radius: var(--rh-radius-sm);
  background: var(--rh-bg-card);
  color: var(--rh-text-primary);
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  transition: var(--rh-transition-all-normal);
}

.backlink-item:hover {
  border-color: var(--rh-primary-muted);
  background: var(--rh-bg-hover);
  color: var(--rh-primary);
}

.backlink-item :deep(.el-icon) {
  flex-shrink: 0;
  color: var(--rh-primary);
}

.backlink-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.backlink-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 引用处上下文片段：单行截断，弱化展示 */
.backlink-context {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--rh-text-tertiary);
  font-size: 12px;
}

.backlink-time {
  flex-shrink: 0;
  color: var(--rh-text-tertiary);
  font-size: 12px;
}
</style>

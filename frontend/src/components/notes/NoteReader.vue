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
        <el-button size="small" type="primary" @click="$emit('edit')">
          <el-icon><Edit /></el-icon> 编辑
        </el-button>
        <el-button size="small" type="danger" @click="handleDelete">
          <el-icon><Delete /></el-icon> 删除
        </el-button>
      </div>
    </div>

    <div class="reader-body">
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

      <div class="note-content" v-html="sanitizedContent" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ArrowLeft, Top, Edit, Delete } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'
import type { Note } from '../../api/notes'

const md = new MarkdownIt({ html: false, linkify: true, typographer: true })

const props = defineProps<{
  note: Note
}>()

const emit = defineEmits<{
  back: []
  edit: []
  'delete': [id: number]
  'togglePin': [id: number]
}>()

function isHtml(str: string): boolean {
  return /<[a-z][\s\S]*>/i.test(str)
}

const sanitizedContent = computed(() => {
  const raw = props.note.content || ''
  // If content is HTML (from TipTap), sanitize and render directly
  // Otherwise, render markdown to HTML first
  const html = isHtml(raw) ? raw : md.render(raw)
  return DOMPurify.sanitize(html)
})

function formatTime(dateStr: string) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('zh-CN')
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
  padding: 24px 32px;
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

.note-content :deep(h1),
.note-content :deep(h2),
.note-content :deep(h3) {
  margin-top: 28px;
  margin-bottom: 12px;
  font-weight: 600;
}

.note-content :deep(h1) {
  font-size: 24px;
  border-bottom: 1px solid var(--rh-border-light);
  padding-bottom: 8px;
}

.note-content :deep(h2) {
  font-size: 20px;
  border-bottom: 1px solid var(--rh-border-light);
  padding-bottom: 6px;
}

.note-content :deep(h3) {
  font-size: 17px;
}

.note-content :deep(p) {
  margin-bottom: 16px;
}

.note-content :deep(code) {
  background: var(--rh-bg-subtle);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 14px;
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  color: var(--rh-primary);
}

.note-content :deep(pre) {
  background: #1c1917;
  padding: 20px;
  border-radius: 10px;
  overflow-x: auto;
  margin: 20px 0;
}

.note-content :deep(pre code) {
  background: none;
  padding: 0;
  color: #e7e5e4;
  font-size: 13.5px;
  line-height: 1.6;
}

.note-content :deep(blockquote) {
  border-left: 3px solid var(--rh-primary);
  padding: 4px 0 4px 20px;
  color: var(--rh-text-secondary);
  margin: 20px 0;
  background: var(--rh-bg-subtle);
  border-radius: 0 8px 8px 0;
}

.note-content :deep(img) {
  max-width: 100%;
  border-radius: 8px;
  margin: 16px 0;
}

.note-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
}

.note-content :deep(th),
.note-content :deep(td) {
  border: 1px solid var(--rh-border);
  padding: 8px 12px;
  text-align: left;
  font-size: 14px;
}

.note-content :deep(th) {
  background: var(--rh-bg-subtle);
  font-weight: 600;
}
</style>

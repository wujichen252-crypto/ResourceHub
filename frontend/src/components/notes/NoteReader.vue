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

      <div class="note-content rh-markdown" v-html="sanitizedContent" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ArrowLeft, Top, Edit, Delete, Promotion } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'
import type { Note } from '../../api/notes'
import { formatDateTime } from '../../utils/format'

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
</style>

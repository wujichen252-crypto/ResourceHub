<template>
  <div class="settings-page">
    <div class="page-heading">
      <h1 class="page-title">设置</h1>
      <p class="page-desc">管理你的账户和数据</p>
    </div>

    <el-card shadow="never" class="settings-card">
      <template #header>
        <span>个人信息</span>
      </template>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="用户名">{{ authStore.user?.username || '-' }}</el-descriptions-item>
        <el-descriptions-item label="邮箱">{{ authStore.user?.email || '未设置' }}</el-descriptions-item>
        <el-descriptions-item label="注册时间">
          {{ authStore.user?.created_at ? new Date(authStore.user.created_at).toLocaleDateString() : '-' }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card shadow="never" class="settings-card">
      <template #header>
        <span>数据导出</span>
      </template>
      <p class="settings-desc">将您的数据导出为 JSON 或 Markdown 格式，便于备份和迁移。</p>
      <div class="export-buttons">
        <el-button type="primary" @click="exportNotes('json')" :loading="exporting">
          <el-icon><Download /></el-icon> 导出笔记 (JSON)
        </el-button>
        <el-button type="success" @click="exportNotes('markdown')" :loading="exporting">
          <el-icon><Download /></el-icon> 导出笔记 (Markdown)
        </el-button>
        <el-button type="warning" @click="exportPrompts" :loading="exporting">
          <el-icon><Download /></el-icon> 导出提示词 (JSON)
        </el-button>
      </div>
    </el-card>

    <el-card shadow="never" class="settings-card">
      <template #header>
        <span>关于</span>
      </template>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="项目名称">ResourceHub</el-descriptions-item>
        <el-descriptions-item label="版本">v0.1.0 (MVP)</el-descriptions-item>
        <el-descriptions-item label="技术栈">Vue 3 + FastAPI + SQLAlchemy</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import http from '../api/http'

const authStore = useAuthStore()
const exporting = ref(false)

async function exportNotes(format: 'json' | 'markdown') {
  exporting.value = true
  try {
    const response = await http.get(`/notes`, {
      params: { page_size: 1000 },
    })
    const notes = response.data.data

    if (format === 'json') {
      downloadFile(JSON.stringify(notes, null, 2), 'notes-export.json', 'application/json')
    } else {
      let md = '# ResourceHub 笔记导出\n\n'
      for (const note of notes) {
        md += `## ${note.title}\n\n`
        if (note.tags?.length) md += `标签: ${note.tags.join(', ')}\n\n`
        md += `${note.content || ''}\n\n---\n\n`
      }
      downloadFile(md, 'notes-export.md', 'text/markdown')
    }
    ElMessage.success('导出成功')
  } catch {
    ElMessage.error('导出失败，请稍后重试')
  } finally {
    exporting.value = false
  }
}

async function exportPrompts() {
  exporting.value = true
  try {
    const response = await http.get('/prompts', {
      params: { page_size: 1000 },
    })
    const data = response.data.data
    downloadFile(JSON.stringify(data, null, 2), 'prompts-export.json', 'application/json')
    ElMessage.success('导出成功')
  } catch {
    ElMessage.error('导出失败，请稍后重试')
  } finally {
    exporting.value = false
  }
}

function downloadFile(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.settings-page {
  padding: 32px;
  max-width: 800px;
  margin: 0 auto;
}

.page-heading {
  margin-bottom: 28px;
}

.page-title {
  font-size: 26px;
  font-weight: 700;
  color: var(--rh-text-primary);
  margin: 0 0 4px;
}

.page-desc {
  font-size: 14px;
  color: var(--rh-text-tertiary);
  margin: 0;
}

.settings-card {
  margin-bottom: 24px;
}

.settings-card :deep(.el-card__header) {
  padding: 16px 24px;
  border-bottom: 1px solid var(--rh-border-light);
  font-weight: 600;
  font-size: 15px;
  color: var(--rh-text-primary);
}

.settings-card :deep(.el-card__body) {
  padding: 24px;
}

.settings-desc {
  font-size: 14px;
  color: var(--rh-text-secondary);
  margin-bottom: 16px;
  line-height: 1.6;
}

.export-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.export-buttons .el-button {
  padding: 10px 20px;
}
</style>

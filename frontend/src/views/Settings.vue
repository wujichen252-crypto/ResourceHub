<template>
  <div class="rh-page rh-page--narrow">
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
          {{ formatDate(authStore.user?.created_at) || '-' }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card shadow="never" class="settings-card">
      <template #header>
        <span>外观</span>
      </template>
      <p class="settings-desc">选择界面配色。选择「跟随系统」时会随操作系统外观自动切换。</p>
      <el-radio-group :model-value="preference" @change="onThemeChange">
        <el-radio-button value="light">浅色</el-radio-button>
        <el-radio-button value="dark">深色</el-radio-button>
        <el-radio-button value="system">跟随系统</el-radio-button>
      </el-radio-group>
    </el-card>

    <el-card shadow="never" class="settings-card">
      <template #header>
        <span>修改密码</span>
      </template>
      <el-form
        ref="passwordFormRef"
        :model="passwordForm"
        :rules="passwordRules"
        label-position="top"
        class="password-form"
      >
        <el-form-item label="原密码" prop="oldPassword">
          <el-input v-model="passwordForm.oldPassword" type="password" show-password placeholder="请输入当前密码" />
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input v-model="passwordForm.newPassword" type="password" show-password placeholder="至少 8 位" />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirmPassword">
          <el-input v-model="passwordForm.confirmPassword" type="password" show-password placeholder="再次输入新密码" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="changingPassword" @click="handleChangePassword">
            修改密码
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="settings-card">
      <template #header>
        <span>数据导出</span>
      </template>
      <p class="settings-desc">将您的数据导出为 JSON 或 Markdown 格式，便于备份和迁移。</p>
      <div class="export-buttons">
        <el-button @click="exportNotes('json')" :loading="exporting">
          <el-icon><Download /></el-icon> 导出笔记 (JSON)
        </el-button>
        <el-button @click="exportNotes('markdown')" :loading="exporting">
          <el-icon><Download /></el-icon> 导出笔记 (Markdown)
        </el-button>
        <el-button @click="exportPrompts" :loading="exporting">
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
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import { authApi } from '../api/auth'
import http from '../api/http'
import { useTheme } from '../composables/useTheme'
import { formatDate } from '../utils/format'

const authStore = useAuthStore()
const { preference, setPreference } = useTheme()
const exporting = ref(false)
const changingPassword = ref(false)
const passwordFormRef = ref<FormInstance>()

/** 外观偏好切换（含「跟随系统」） */
function onThemeChange(value: string | number | boolean | undefined) {
  if (value === 'light' || value === 'dark' || value === 'system') setPreference(value)
}

const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const validateConfirm = (_rule: any, value: string, callback: Function) => {
  if (value !== passwordForm.newPassword) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const passwordRules: FormRules = {
  oldPassword: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '密码长度至少 8 位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: validateConfirm, trigger: 'blur' },
  ],
}

async function handleChangePassword() {
  const valid = await passwordFormRef.value?.validate().catch(() => false)
  if (!valid) return
  changingPassword.value = true
  try {
    await authApi.changePassword({
      old_password: passwordForm.oldPassword,
      new_password: passwordForm.newPassword,
    })
    ElMessage.success('密码修改成功')
    passwordForm.oldPassword = ''
    passwordForm.newPassword = ''
    passwordForm.confirmPassword = ''
  } catch (err: any) {
    ElMessage.error(err.response?.data?.msg || '密码修改失败')
  } finally {
    changingPassword.value = false
  }
}

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
    warnIfTruncated(notes.length)
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
    warnIfTruncated(data.length)
  } catch {
    ElMessage.error('导出失败，请稍后重试')
  } finally {
    exporting.value = false
  }
}

/** 导出条目数达到分页上限时，明确告知数据可能不完整（原先会静默截断） */
function warnIfTruncated(count: number) {
  if (count >= 1000) ElMessage.warning('导出内容已达 1000 条上限，可能存在数据未导出')
  else ElMessage.success('导出成功')
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
.page-heading {
  margin-bottom: 28px;
}

.page-title {
  font-family: var(--rh-font-display);
  font-size: 26px;
  font-weight: 500;
  color: var(--rh-text-primary);
  margin: 0 0 4px;
}

.page-desc {
  font-size: 14px;
  color: var(--rh-text-tertiary);
  margin: 0;
}

.settings-card {
  margin-bottom: 20px;
}

.settings-card :deep(.el-card__header) {
  padding: 14px 20px;
  border-bottom: 1px solid var(--rh-border-faint);
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

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
      <el-descriptions :column="1" border label-width="120px">
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
        <span>标签管理</span>
      </template>
      <p class="settings-desc">标签以自由文本保存，这里可以统一重命名、合并同类标签或清理不再使用的标签。改动会直接更新所有已关联的笔记 / 提示词。</p>
      <el-tabs v-model="tagScope" @tab-change="loadTags">
        <el-tab-pane label="笔记标签" name="note" />
        <el-tab-pane label="提示词标签" name="prompt" />
      </el-tabs>
      <div class="tag-toolbar">
        <el-button :disabled="selectedTags.length < 2" @click="handleMergeTags">
          合并所选{{ selectedTags.length >= 2 ? `（${selectedTags.length}）` : '' }}
        </el-button>
        <span class="tag-hint">勾选两个及以上标签，合并为同一个名称</span>
      </div>
      <el-table
        v-if="tagList.length"
        v-loading="tagsLoading"
        :data="tagList"
        row-key="name"
        @selection-change="onTagSelectionChange"
      >
        <el-table-column type="selection" width="44" />
        <el-table-column prop="name" label="标签" min-width="160" />
        <el-table-column prop="count" :label="tagScope === 'note' ? '笔记数' : '提示词数'" width="100" />
        <el-table-column label="操作" width="160" align="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleRenameTag(row)">重命名</el-button>
            <el-button link type="danger" @click="handleDeleteTag(row)">清理</el-button>
          </template>
        </el-table-column>
      </el-table>
      <EmptyState
        v-else-if="!tagsLoading"
        title="暂无标签"
        description="给笔记或提示词打上标签后，就可以在这里统一管理。"
        min-height="160px"
      />
    </el-card>

    <el-card shadow="never" class="settings-card">
      <template #header>
        <span>数据导入导出</span>
      </template>
      <p class="settings-desc">Markdown 导出会打包为 zip，每篇笔记一个 .md（带标题与标签）；导入支持 .md / .markdown / .zip 压缩包，同目录同名笔记会被覆盖。</p>
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
      <el-divider />
      <div class="import-row">
        <el-upload
          ref="uploadRef"
          :auto-upload="false"
          multiple
          accept=".md,.markdown,.zip"
          :limit="200"
          :on-change="onImportFilesChange"
          :on-remove="onImportFilesChange"
          :on-exceed="onImportExceed"
        >
          <el-button>选择 Markdown / ZIP 文件</el-button>
        </el-upload>
        <el-button type="primary" :loading="importing" :disabled="!hasImportFiles" @click="handleImport">
          开始导入
        </el-button>
      </div>
      <p class="settings-desc import-hint">单文件 ≤ 2MB，单次最多 200 篇；导入的笔记进入「未分类」。</p>
    </el-card>

    <el-card shadow="never" class="settings-card">
      <template #header>
        <span>关于</span>
      </template>
      <el-descriptions :column="1" border label-width="120px">
        <el-descriptions-item label="项目名称">ResourceHub</el-descriptions-item>
        <el-descriptions-item label="版本">v0.1.0 (MVP)</el-descriptions-item>
        <el-descriptions-item label="技术栈">Vue 3 + FastAPI + SQLAlchemy</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import { authApi } from '../api/auth'
import http from '../api/http'
import { notesApi } from '../api/notes'
import { tagsApi } from '../api/tags'
import type { TagCount, TagScope } from '../api/tags'
import { useTheme } from '../composables/useTheme'
import { formatDate } from '../utils/format'
import EmptyState from '../components/common/EmptyState.vue'

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

const uploadRef = ref<any>()
const importFiles = ref<any[]>([])
const importing = ref(false)
const hasImportFiles = computed(() => importFiles.value.length > 0)

function onImportFilesChange(_file: any, files: any[]) {
  importFiles.value = files
}

function onImportExceed() {
  ElMessage.warning('单次最多导入 200 个文件')
}

async function handleImport() {
  const raws = importFiles.value.map((file) => file.raw).filter(Boolean) as File[]
  if (!raws.length) return
  importing.value = true
  try {
    const result = await notesApi.importMarkdown(raws)
    ElMessage.success(`导入完成：新增 ${result.created} 篇，覆盖 ${result.replaced} 篇`)
    if (result.skipped.length) {
      const first = result.skipped[0]
      ElMessage.warning(`跳过 ${result.skipped.length} 个文件（如 ${first.file}：${first.reason}）`)
    }
    uploadRef.value?.clearFiles()
    importFiles.value = []
  } catch (err: any) {
    ElMessage.error(err.response?.data?.msg || '导入失败，请稍后重试')
  } finally {
    importing.value = false
  }
}

async function exportNotes(format: 'json' | 'markdown') {
  exporting.value = true
  try {
    const stamp = new Date().toISOString().slice(0, 10).replace(/-/g, '')
    if (format === 'markdown') {
      downloadBlob(await notesApi.exportMarkdown(), `resourcehub-notes-${stamp}.zip`)
    } else {
      downloadBlob(await notesApi.exportJson(), `resourcehub-notes-${stamp}.json`)
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
    const items: any[] = []
    let total = 0
    for (let page = 1; page <= 20; page += 1) {
      const chunk = (await http.get('/prompts', {
        params: { page, page_size: 100 },
      })) as { items: any[]; total: number }
      total = chunk.total
      items.push(...chunk.items)
      if (items.length >= total) break
    }
    downloadFile(JSON.stringify(items, null, 2), 'prompts-export.json', 'application/json')
    if (items.length < total) ElMessage.warning(`提示词共 ${total} 条，本次导出 ${items.length} 条`)
    else ElMessage.success('导出成功')
  } catch {
    ElMessage.error('导出失败，请稍后重试')
  } finally {
    exporting.value = false
  }
}

function downloadFile(content: string, filename: string, mimeType: string) {
  downloadBlob(new Blob([content], { type: mimeType }), filename)
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// ── 标签管理 ──────────────────────────────────────
const tagScope = ref<TagScope>('note')
const tagList = ref<TagCount[]>([])
const tagsLoading = ref(false)
const selectedTags = ref<TagCount[]>([])

async function loadTags() {
  tagsLoading.value = true
  selectedTags.value = []
  try {
    const { items } = await tagsApi.list(tagScope.value)
    tagList.value = items
  } catch {
    // 拦截器已提示具体错误，这里保持列表可用
  } finally {
    tagsLoading.value = false
  }
}

function onTagSelectionChange(rows: TagCount[]) {
  selectedTags.value = rows
}

function tagUnit() {
  return tagScope.value === 'note' ? '笔记' : '提示词'
}

async function handleRenameTag(row: TagCount) {
  let value: string
  try {
    const result = await ElMessageBox.prompt(
      `将同步更新所有已关联的${tagUnit()}。`,
      `重命名「${row.name}」`,
      {
        inputValue: row.name,
        inputValidator: (v: string) => (v && v.trim() ? true : '标签名不能为空'),
        inputErrorMessage: '标签名不能为空',
        confirmButtonText: '保存',
        cancelButtonText: '取消',
      },
    )
    value = result.value.trim()
  } catch {
    return
  }
  if (value === row.name) return
  try {
    const { updated } = await tagsApi.rename(tagScope.value, row.name, value)
    ElMessage.success(`已重命名，更新 ${updated} 条`)
    await loadTags()
  } catch {
    // 拦截器已提示
  }
}

async function handleMergeTags() {
  const sources = selectedTags.value.map((tag) => tag.name)
  if (sources.length < 2) return
  let target: string
  try {
    const result = await ElMessageBox.prompt(
      `将 ${sources.map((name) => `「${name}」`).join('、')} 合并为一个标签。`,
      '合并标签',
      {
        inputPlaceholder: '合并后的标签名',
        inputValidator: (v: string) => (v && v.trim() ? true : '请输入目标标签名'),
        inputErrorMessage: '请输入目标标签名',
        confirmButtonText: '合并',
        cancelButtonText: '取消',
      },
    )
    target = result.value.trim()
  } catch {
    return
  }
  try {
    const { updated } = await tagsApi.merge(tagScope.value, sources, target)
    ElMessage.success(`已合并，更新 ${updated} 条`)
    await loadTags()
  } catch {
    // 拦截器已提示
  }
}

async function handleDeleteTag(row: TagCount) {
  try {
    await ElMessageBox.confirm(
      `将从 ${row.count} 条${tagUnit()}中移除标签「${row.name}」，此操作不可撤销。`,
      '清理标签',
      { type: 'error', confirmButtonText: '清理', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    const { updated } = await tagsApi.remove(tagScope.value, row.name)
    ElMessage.success(`已清理，更新 ${updated} 条`)
    await loadTags()
  } catch {
    // 拦截器已提示
  }
}

onMounted(loadTags)
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

.import-row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 12px;
}

.settings-desc.import-hint {
  margin-top: 12px;
  margin-bottom: 0;
  font-size: 13px;
  color: var(--rh-text-tertiary);
}

.tag-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.tag-hint {
  font-size: 13px;
  color: var(--rh-text-tertiary);
}
</style>

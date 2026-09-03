<template>
  <el-drawer
    v-model="drawerVisible"
    title="版本历史"
    size="700px"
    @open="loadData"
  >
    <div class="version-layout">
      <!-- Left: Version List -->
      <div class="version-list">
        <div
          v-for="v in promptsStore.versions"
          :key="v.id"
          class="version-item"
          :class="{
            current: v.version_number === currentVersion,
            selected: selectedVersionId === v.id,
          }"
          @click="selectVersion(v)"
        >
          <div class="vi-header">
            <span class="vi-badge" :class="{ 'is-current': v.version_number === currentVersion }">
              v{{ v.version_number }}
            </span>
            <span v-if="v.version_number === currentVersion" class="vi-current-tag">当前</span>
            <span class="vi-time">{{ relativeTime(v.created_at) }}</span>
          </div>
          <div class="vi-message">{{ v.message || '无描述' }}</div>
          <div class="vi-meta">
            <el-tag
              v-for="label in v.labels"
              :key="label"
              size="small"
              :type="label === 'production' ? 'success' : label === 'staging' ? 'warning' : 'info'"
            >{{ label }}</el-tag>
          </div>
        </div>
        <div v-if="promptsStore.versions.length === 0" class="empty-list">
          暂无历史版本
        </div>
      </div>

      <!-- Right: Diff Preview -->
      <div class="diff-panel">
        <div v-if="!promptsStore.currentDiff && !selectedVersionId" class="diff-placeholder">
          <p>点击一个版本选中，再点击另一个版本对比差异</p>
        </div>
        <div v-else-if="!promptsStore.currentDiff && selectedVersionId" class="diff-placeholder">
          <p>已选中 v{{ getVersionNumber(selectedVersionId) }}，请再点击另一个版本进行对比</p>
        </div>
        <div v-else-if="promptsStore.diffLoading" v-loading="promptsStore.diffLoading" class="diff-loading" />
        <div v-else class="diff-content">
          <div class="diff-header">
            <span class="diff-label">
              v{{ promptsStore.currentDiff.v1.version_number }} → v{{ promptsStore.currentDiff.v2.version_number }}
            </span>
            <div class="diff-actions">
              <el-button size="small" text @click="handleRestore(selectedVersionId)">
                <el-icon><Refresh /></el-icon> 恢复到此版本
              </el-button>
              <el-dropdown trigger="click" @command="handleLabelAction">
                <el-button size="small" text>
                  <el-icon><PriceTag /></el-icon> 标签
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="production">🏷 production</el-dropdown-item>
                    <el-dropdown-item command="staging">🏷 staging</el-dropdown-item>
                    <el-dropdown-item command="draft">🏷 draft</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>
          <div class="diff-lines">
            <div
              v-for="(seg, i) in promptsStore.currentDiff.diffs"
              :key="i"
              class="diff-line"
              :class="'diff-' + seg.type"
            >
              <span class="diff-marker">{{ seg.type === 'insert' ? '+' : seg.type === 'delete' ? '-' : ' ' }}</span>
              <span class="diff-text">{{ seg.value }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, PriceTag } from '@element-plus/icons-vue'
import { usePromptsStore } from '../../stores/prompts'
import type { PromptVersion } from '../../api/prompts'

const props = defineProps<{
  modelValue: boolean
  promptId: number | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  restored: []
}>()

const promptsStore = usePromptsStore()
const drawerVisible = ref(props.modelValue)
const selectedVersionId = ref<number | null>(null)
const currentVersion = ref(0)

watch(() => props.modelValue, (v) => { drawerVisible.value = v })
watch(drawerVisible, (v) => emit('update:modelValue', v))

async function loadData() {
  if (!props.promptId) return
  selectedVersionId.value = null
  promptsStore.currentDiff = null
  await promptsStore.fetchVersions(props.promptId)
  if (promptsStore.versions.length > 0) {
    currentVersion.value = promptsStore.versions[0].version_number
  }
}

function selectVersion(v: PromptVersion) {
  if (!selectedVersionId.value) {
    selectedVersionId.value = v.id
    return
  }
  // If same, deselect
  if (selectedVersionId.value === v.id) {
    selectedVersionId.value = null
    promptsStore.currentDiff = null
    return
  }
  // Load diff between selected and clicked
  const v1Id = selectedVersionId.value
  const v2Id = v.id
  selectedVersionId.value = v2Id
  if (props.promptId) {
    promptsStore.fetchDiff(props.promptId, v1Id, v2Id)
  }
}

async function handleRestore(versionId: number | null) {
  if (!versionId || !props.promptId) return
  const v = promptsStore.versions.find((x) => x.id === versionId)
  if (!v) return
  try {
    await ElMessageBox.confirm(
      `确定要恢复到 v${v.version_number} 吗？当前内容将被保存为新版本。`,
      '确认恢复',
      { confirmButtonText: '恢复', cancelButtonText: '取消', type: 'warning' },
    )
    await promptsStore.restoreVersion(props.promptId, versionId)
    ElMessage.success(`已恢复到 v${v.version_number}`)
    emit('restored')
  } catch {
    // cancelled
  }
}

async function handleLabelAction(label: string) {
  if (!selectedVersionId.value || !props.promptId) return
  const v = promptsStore.versions.find((x) => x.id === selectedVersionId.value)
  if (!v) return
  const current = v.labels || []
  const newLabels = current.includes(label)
    ? current.filter((l) => l !== label)
    : [...current, label]
  await promptsStore.updateVersionLabels(props.promptId, selectedVersionId.value, newLabels)
  ElMessage.success(current.includes(label) ? `已移除 ${label} 标签` : `已添加 ${label} 标签`)
}

function getVersionNumber(versionId: number): number {
  const v = promptsStore.versions.find((x) => x.id === versionId)
  return v?.version_number ?? 0
}

function relativeTime(dateStr: string) {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return '刚刚'
  if (mins < 60) return `${mins}分钟前`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}小时前`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days}天前`
  return new Date(dateStr).toLocaleDateString('zh-CN')
}
</script>

<style scoped>
.version-layout {
  display: flex;
  height: 100%;
  gap: 16px;
}

/* Left list */
.version-list {
  width: 240px;
  flex-shrink: 0;
  overflow-y: auto;
  border-right: 1px solid var(--rh-border-light);
  padding-right: 12px;
}

.version-item {
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: var(--rh-transition);
  margin-bottom: 4px;
  border: 1px solid transparent;
}

.version-item:hover {
  background: var(--rh-bg-hover);
}

.version-item.selected {
  border-color: var(--rh-primary);
  background: var(--rh-primary-lighter);
}

.version-item.current {
  background: var(--rh-primary-lighter);
}

.vi-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.vi-badge {
  font-size: 11px;
  font-weight: 600;
  color: var(--rh-primary);
  background: var(--rh-primary-lighter);
  padding: 1px 6px;
  border-radius: 4px;
  font-family: monospace;
}

.vi-badge.is-current {
  background: var(--rh-primary);
  color: #fff;
}

.vi-current-tag {
  font-size: 11px;
  color: #10b981;
  font-weight: 600;
}

.vi-time {
  margin-left: auto;
  font-size: 11px;
  color: var(--rh-text-tertiary);
  white-space: nowrap;
}

.vi-message {
  font-size: 13px;
  color: var(--rh-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 4px;
}

.vi-meta {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.empty-list {
  text-align: center;
  color: var(--rh-text-tertiary);
  padding: 32px 0;
  font-size: 14px;
}

/* Right diff panel */
.diff-panel {
  flex: 1;
  overflow-y: auto;
  min-height: 300px;
}

.diff-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--rh-text-tertiary);
  font-size: 14px;
}

.diff-loading {
  min-height: 200px;
}

.diff-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--rh-border-light);
}

.diff-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--rh-text-primary);
  font-family: monospace;
}

.diff-actions {
  display: flex;
  gap: 4px;
}

.diff-lines {
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.6;
}

.diff-line {
  display: flex;
  padding: 1px 4px;
  border-radius: 2px;
}

.diff-marker {
  width: 16px;
  flex-shrink: 0;
  color: var(--rh-text-tertiary);
  user-select: none;
}

.diff-text {
  flex: 1;
  white-space: pre-wrap;
  word-break: break-all;
}

.diff-insert {
  background: #ecfdf5;
}

.diff-insert .diff-marker {
  color: #10b981;
}

.diff-delete {
  background: #fef2f2;
}

.diff-delete .diff-marker {
  color: #ef4444;
}
</style>

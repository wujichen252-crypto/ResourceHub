<template>
  <el-drawer
    v-model="drawerVisible"
    title="版本历史"
    size="min(700px, 100vw)"
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
            <span class="vi-time">{{ formatRelative(v.created_at) }}</span>
          </div>
          <div class="vi-message">{{ v.message || '无描述' }}</div>
          <div class="vi-meta">
            <el-tag
              v-for="label in v.labels"
              :key="label"
              size="small"
              :type="label === 'production' ? 'success' : label === 'staging' ? 'warning' : 'info'"
            >{{ labelText(label) }}</el-tag>
          </div>
        </div>
        <div v-if="promptsStore.versions.length === 0" class="empty-list">
          暂无历史版本
        </div>
      </div>

      <!-- Right: Diff Preview -->
      <div class="diff-panel">
        <div v-if="promptsStore.diffLoading" v-loading="promptsStore.diffLoading" class="diff-loading" />

        <div v-else-if="currentDiff || fullVersion" class="diff-content">
          <div class="diff-header">
            <span class="diff-label">{{ activeHeadline }}</span>
            <div class="diff-actions">
              <el-button size="small" text @click="handleRestore(selectedVersionId)">
                <el-icon><Refresh /></el-icon> 恢复到此版本
              </el-button>
              <el-dropdown trigger="click" @command="handleLabelAction">
                <el-button size="small" text>
                  <el-icon><PriceTag /></el-icon> 标记
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="production">🏷 生产</el-dropdown-item>
                    <el-dropdown-item command="staging">🏷 预发布</el-dropdown-item>
                    <el-dropdown-item command="draft">🏷 草稿</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>

          <!-- 有对比基准：展示增删统计、其他字段变更与正文对比 -->
          <template v-if="currentDiff">
            <div class="diff-summary">
              <span v-if="diffStats.added" class="summary-add">新增 {{ diffStats.added }} 行</span>
              <span v-if="diffStats.removed" class="summary-del">删除 {{ diffStats.removed }} 行</span>
              <span v-if="!diffStats.changed" class="summary-same">正文内容没有变化</span>
            </div>

            <section v-if="metaChanges.length" class="diff-section">
              <h4 class="diff-section-title">其他信息变更</h4>
              <div v-for="change in metaChanges" :key="change.field" class="meta-row">
                <span class="meta-field">{{ change.field }}</span>
                <span class="meta-old">{{ change.before }}</span>
                <el-icon class="meta-arrow"><Right /></el-icon>
                <span class="meta-new">{{ change.after }}</span>
              </div>
            </section>

            <section class="diff-section">
              <h4 class="diff-section-title">正文对比</h4>
              <div class="diff-lines">
                <div
                  v-for="(seg, i) in diffForView.diffs"
                  :key="i"
                  class="diff-line"
                  :class="'diff-' + seg.type"
                >
                  <span class="diff-marker">{{ seg.type === 'insert' ? '+' : seg.type === 'delete' ? '-' : ' ' }}</span>
                  <span class="diff-text">{{ seg.value || ' ' }}</span>
                </div>
              </div>
            </section>
          </template>

          <!-- 最早版本没有对比基准：直接展示完整内容 -->
          <template v-else>
            <div class="diff-summary">
              <span class="summary-same">这是最早的版本，暂无更早版本可对比，下方为完整内容</span>
            </div>
            <div class="diff-lines">
              <div v-for="(line, i) in fullLines" :key="i" class="diff-line">
                <span class="full-line-no">{{ i + 1 }}</span>
                <span class="diff-text">{{ line || ' ' }}</span>
              </div>
            </div>
          </template>
        </div>

        <div v-else class="diff-placeholder">
          <p>点击左侧任意版本，即可查看它相对上一版修改了什么</p>
        </div>
      </div>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, PriceTag, Right } from '@element-plus/icons-vue'
import { usePromptsStore } from '../../stores/prompts'
import type { PromptVersion } from '../../api/prompts'
import { formatRelative } from '../../utils/format'

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
/** 最早版本没有对比基准时，直接展示的完整版本内容 */
const fullVersion = ref<PromptVersion | null>(null)
const currentDiff = computed(() => promptsStore.currentDiff)
const diffForView = computed(() => currentDiff.value || { v1: { version_number: 0 }, v2: { version_number: 0 }, diffs: [] })
const currentVersion = ref(0)

/** 版本标记的中文文案，未知标记原样显示 */
const LABEL_TEXT: Record<string, string> = {
  production: '生产',
  staging: '预发布',
  draft: '草稿',
}

function labelText(label: string): string {
  return LABEL_TEXT[label] ?? label
}

/** 右侧面板标题：有对比时显示「旧 → 新」，无基准时显示初始版本 */
const activeHeadline = computed(() => {
  if (currentDiff.value) {
    return `v${currentDiff.value.v1.version_number} → v${currentDiff.value.v2.version_number}`
  }
  if (fullVersion.value) return `v${fullVersion.value.version_number} 初始版本`
  return ''
})

/** 正文增删行数统计 */
const diffStats = computed(() => {
  let added = 0
  let removed = 0
  for (const seg of currentDiff.value?.diffs ?? []) {
    if (seg.type === 'insert') added++
    else if (seg.type === 'delete') removed++
  }
  return { added, removed, changed: added > 0 || removed > 0 }
})

/** 初始版本的完整正文按行拆分，用于展示行号 */
const fullLines = computed(() => {
  const content = fullVersion.value?.content ?? ''
  if (!content) return ['（该版本内容为空）']
  return content.replace(/\r\n/g, '\n').split('\n')
})

/** 正文之外发生变化的字段（标题 / 描述 / 变量 / 标签 / 标记） */
const metaChanges = computed(() => {
  const diff = currentDiff.value
  if (!diff) return []
  const fields = [
    { field: '标题', before: formatMetaValue(diff.v1.title), after: formatMetaValue(diff.v2.title) },
    { field: '描述', before: formatMetaValue(diff.v1.description), after: formatMetaValue(diff.v2.description) },
    { field: '变量', before: formatMetaValue(diff.v1.variables), after: formatMetaValue(diff.v2.variables) },
    { field: '标签', before: formatMetaValue(diff.v1.tags), after: formatMetaValue(diff.v2.tags) },
    {
      field: '版本标记',
      before: formatMetaValue(diff.v1.labels.map(labelText)),
      after: formatMetaValue(diff.v2.labels.map(labelText)),
    },
  ]
  return fields.filter((item) => item.before !== item.after)
})

function formatMetaValue(value: string | string[] | null | undefined): string {
  if (Array.isArray(value)) return value.length > 0 ? value.join('、') : '无'
  const text = (value ?? '').trim()
  return text || '无'
}

watch(() => props.modelValue, (v) => { drawerVisible.value = v })
watch(drawerVisible, (v) => emit('update:modelValue', v))

async function loadData() {
  if (!props.promptId) return
  selectedVersionId.value = null
  fullVersion.value = null
  promptsStore.currentDiff = null
  await promptsStore.fetchVersions(props.promptId)
  if (promptsStore.versions.length > 0) {
    currentVersion.value = promptsStore.versions[0].version_number
    // 打开面板默认对比最新版本与上一版，避免右侧一开始就是空白
    selectVersion(promptsStore.versions[0])
  }
}

/**
 * 点击版本即自动与更早的相邻版本对比，让用户直接看到改了哪些地方。
 * 最早版本没有对比基准时，改为展示该版本的完整内容。
 */
function selectVersion(v: PromptVersion) {
  selectedVersionId.value = v.id
  // 取版本号更小的最近一版作为基准，保证对比方向始终是「旧 → 新」
  const baseVersion = promptsStore.versions
    .filter((item) => item.version_number < v.version_number)
    .sort((a, b) => b.version_number - a.version_number)[0]

  if (baseVersion && props.promptId) {
    fullVersion.value = null
    promptsStore.fetchDiff(props.promptId, baseVersion.id, v.id).catch(() => {
      ElMessage.error('版本对比加载失败，请稍后重试')
    })
    return
  }

  promptsStore.currentDiff = null
  fullVersion.value = v
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
  ElMessage.success(
    current.includes(label) ? `已移除「${labelText(label)}」标记` : `已添加「${labelText(label)}」标记`,
  )
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
  border-radius: var(--rh-radius-md);
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
  border-radius: var(--rh-radius-xs);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

.vi-badge.is-current {
  background: var(--rh-primary);
  color: var(--rh-on-primary);
}

.vi-current-tag {
  font-size: 11px;
  color: var(--rh-success-strong);
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

/* 变更统计 */
.diff-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 12px;
}

.summary-add {
  color: var(--rh-success-strong);
  background: var(--rh-success-subtle);
  padding: 1px 6px;
  border-radius: var(--rh-radius-xs);
}

.summary-del {
  color: var(--rh-danger);
  background: var(--rh-danger-subtle);
  padding: 1px 6px;
  border-radius: var(--rh-radius-xs);
}

.summary-same {
  color: var(--rh-text-tertiary);
}

.diff-section {
  margin-bottom: 16px;
}

.diff-section-title {
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--rh-text-secondary);
  letter-spacing: 0.04em;
}

/* 其他信息变更：旧值划掉，新值高亮 */
.meta-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 6px 8px;
  margin-bottom: 4px;
  border-radius: var(--rh-radius-xs);
  background: var(--rh-bg-hover);
  font-size: 13px;
}

.meta-field {
  flex-shrink: 0;
  width: 64px;
  font-size: 12px;
  color: var(--rh-text-tertiary);
}

.meta-old {
  color: var(--rh-text-secondary);
  text-decoration: line-through;
  word-break: break-all;
}

.meta-arrow {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--rh-text-tertiary);
}

.meta-new {
  color: var(--rh-text-primary);
  word-break: break-all;
}

.diff-lines {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 13px;
  line-height: 1.6;
}

/* 初始版本的行号列 */
.full-line-no {
  flex-shrink: 0;
  width: 28px;
  padding-right: 8px;
  text-align: right;
  color: var(--rh-text-tertiary);
  user-select: none;
  font-variant-numeric: tabular-nums;
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

/* 增删行除颜色外叠加左侧色条，避免红绿色觉障碍下无法区分 */
.diff-insert {
  background: var(--rh-success-subtle);
  box-shadow: inset 2px 0 0 var(--rh-success-strong);
}

.diff-insert .diff-marker {
  color: var(--rh-success-strong);
}

.diff-delete {
  background: var(--rh-danger-subtle);
  box-shadow: inset 2px 0 0 var(--rh-danger);
}

.diff-delete .diff-marker {
  color: var(--rh-danger);
}
</style>

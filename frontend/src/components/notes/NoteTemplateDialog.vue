<template>
  <el-dialog
    :model-value="modelValue"
    title="笔记模板"
    width="640px"
    @update:model-value="(visible: boolean) => emit('update:modelValue', visible)"
    @open="load"
  >
    <div class="template-toolbar">
      <el-button type="primary" @click="startBlank">
        <el-icon><Plus /></el-icon> 空白新建
      </el-button>
      <span class="template-hint">套用模板会带上预设的标题、正文、标签与目录</span>
    </div>

    <LoadingState v-if="loading" variant="row" :count="3" />

    <div v-else-if="templates.length" class="template-list">
      <div v-for="template in templates" :key="template.id" class="template-item">
        <div class="template-info">
          <div class="template-name">{{ template.name }}</div>
          <div class="template-meta">
            <el-tag
              v-for="tag in template.tags"
              :key="tag"
              size="small"
              type="info"
            >{{ tag }}</el-tag>
            <span class="template-time">{{ formatRelative(template.updated_at) }}</span>
          </div>
        </div>
        <div class="template-actions">
          <el-button size="small" type="primary" @click="applyTemplate(template)">套用</el-button>
          <el-button size="small" text @click="renameTemplate(template)">重命名</el-button>
          <el-button size="small" text type="danger" @click="deleteTemplate(template)">删除</el-button>
        </div>
      </div>
    </div>

    <EmptyState
      v-else
      title="还没有模板"
      description="编辑笔记时点击「存为模板」，或空白新建一篇后另存。"
      min-height="200px"
    />
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { noteTemplatesApi } from '../../api/noteTemplates'
import type { NoteTemplate } from '../../api/noteTemplates'
import { formatRelative } from '../../utils/format'
import EmptyState from '../common/EmptyState.vue'
import LoadingState from '../common/LoadingState.vue'

defineProps<{ modelValue: boolean }>()

const emit = defineEmits<{
  'update:modelValue': [visible: boolean]
  apply: [template: NoteTemplate]
  blank: []
}>()

const loading = ref(false)
const templates = ref<NoteTemplate[]>([])

async function load() {
  loading.value = true
  try {
    const { items } = await noteTemplatesApi.list()
    templates.value = items
  } catch {
    // 拦截器已提示
  } finally {
    loading.value = false
  }
}

function startBlank() {
  emit('update:modelValue', false)
  emit('blank')
}

function applyTemplate(template: NoteTemplate) {
  emit('update:modelValue', false)
  emit('apply', template)
}

async function renameTemplate(template: NoteTemplate) {
  let name: string
  try {
    const result = await ElMessageBox.prompt('重命名模板不会影响已创建的笔记。', `重命名「${template.name}」`, {
      inputValue: template.name,
      inputValidator: (value: string) => (value && value.trim() ? true : '模板名称不能为空'),
      inputErrorMessage: '模板名称不能为空',
      confirmButtonText: '保存',
      cancelButtonText: '取消',
    })
    name = result.value.trim()
  } catch {
    return
  }
  if (name === template.name) return
  try {
    const updated = await noteTemplatesApi.update(template.id, { name })
    const index = templates.value.findIndex((item) => item.id === template.id)
    if (index >= 0) templates.value[index] = updated
    ElMessage.success('已重命名')
  } catch {
    // 拦截器已提示
  }
}

async function deleteTemplate(template: NoteTemplate) {
  try {
    await ElMessageBox.confirm(
      `删除模板「${template.name}」？已创建的笔记不受影响。`,
      '删除模板',
      { type: 'error', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await noteTemplatesApi.remove(template.id)
    templates.value = templates.value.filter((item) => item.id !== template.id)
    ElMessage.success('已删除模板')
  } catch {
    // 拦截器已提示
  }
}
</script>

<style scoped>
.template-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.template-hint {
  font-size: 13px;
  color: var(--rh-text-tertiary);
}

.template-list {
  display: flex;
  flex-direction: column;
  max-height: 420px;
  overflow-y: auto;
}

.template-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 4px;
  border-bottom: 1px solid var(--rh-border-faint);
}

.template-item:last-child {
  border-bottom: none;
}

.template-info {
  min-width: 0;
}

.template-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--rh-text-primary);
  margin-bottom: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.template-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 12px;
  color: var(--rh-text-tertiary);
}

.template-time {
  margin-left: 2px;
}

.template-actions {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}
</style>

<template>
  <div class="prompt-detail-page">
    <!-- Page Transition -->
    <Transition name="fade-slide" appear>
      <div v-if="!loading && prompt" class="page-wrapper animate-fade-in-up">
        <!-- Header -->
        <div class="detail-header">
          <el-button text @click="goBack">
            <el-icon><ArrowLeft /></el-icon> 返回列表
          </el-button>
          <div class="detail-actions">
            <el-button @click="toggleFav">
              <el-icon><StarFilled v-if="prompt.is_favorite" /><Star v-else /></el-icon>
              {{ prompt.is_favorite ? '已收藏' : '收藏' }}
            </el-button>
            <el-button @click="showVersionDrawer = true">
              <el-icon><Clock /></el-icon> 历史版本
            </el-button>
            <el-button type="primary" @click="editPrompt">
              <el-icon><Edit /></el-icon> 编辑
            </el-button>
            <el-button type="danger" @click="deletePrompt">
              <el-icon><Delete /></el-icon> 删除
            </el-button>
          </div>
        </div>

        <!-- Two Column Layout -->
        <el-row :gutter="20">
          <!-- Left: Template -->
          <el-col :xs="24" :lg="14">
            <el-card shadow="never" class="section-card">
              <template #header>
                <div class="section-header">
                  <span>提示词模板</span>
                  <el-tag v-if="prompt.category_name" size="small">{{ prompt.category_name }}</el-tag>
                </div>
              </template>

              <h2 class="prompt-title">{{ prompt.title }}</h2>
              <p v-if="prompt.description" class="prompt-desc">{{ prompt.description }}</p>

              <div class="prompt-tags" v-if="prompt.tags?.length">
                <el-tag v-for="t in prompt.tags" :key="t" size="small" type="info">{{ t }}</el-tag>
              </div>

              <div class="usage-stats">使用 {{ prompt.usage_count }} 次</div>

              <pre class="template-content">{{ prompt.content }}</pre>

              <div v-if="prompt.variables?.length" class="variables-display">
                <span class="vars-label">变量:</span>
                <el-tag
                  v-for="v in prompt.variables"
                  :key="v"
                  size="small"
                  type="warning"
                >{{ v }}</el-tag>
              </div>
            </el-card>
          </el-col>

          <!-- Right: Render -->
          <el-col :xs="24" :lg="10">
            <el-card shadow="never" class="section-card">
              <template #header>
                <span>填充变量</span>
              </template>

              <div v-if="!prompt.variables?.length" class="no-vars">
                <p>该提示词没有变量，可以直接复制使用。</p>
                <el-button type="primary" class="copy-btn" @click="copyContent(prompt.content || '')">
                  <el-icon><CopyDocument /></el-icon> 复制提示词
                </el-button>
              </div>

              <template v-else>
                <!-- Live Preview Toggle -->
                <div class="preview-toggle">
                  <el-switch v-model="livePreview" active-text="实时预览" size="small" />
                </div>

                <!-- Live Preview Result -->
                <div v-if="livePreview && livePreviewResult" class="live-preview">
                  <div class="live-preview-header">
                    <span class="live-preview-label">即时预览</span>
                    <el-button size="small" text @click="copyContent(livePreviewResult)">
                      <el-icon><CopyDocument /></el-icon> 复制
                    </el-button>
                  </div>
                  <pre class="live-preview-content">{{ livePreviewResult }}</pre>
                </div>

                <!-- Presets -->
                <div class="presets-section">
                  <el-select
                    v-model="selectedPresetId"
                    placeholder="加载预设"
                    clearable
                    size="small"
                    class="preset-select"
                    @change="handlePresetSelect"
                  >
                    <el-option
                      v-for="p in promptsStore.presets"
                      :key="p.id"
                      :label="p.name"
                      :value="p.id"
                    />
                  </el-select>
                  <el-button size="small" text @click="handleSavePreset">
                    <el-icon><Plus /></el-icon> 另存为
                  </el-button>
                </div>

                <el-form label-position="top">
                  <el-form-item
                    v-for="v in prompt.variables"
                    :key="v"
                    :label="v"
                  >
                    <el-input
                      v-model="variableValues[v]"
                      :placeholder="`请输入 ${v}`"
                      @keyup.enter="handleRender"
                    />
                  </el-form-item>

                  <el-form-item>
                    <el-button type="primary" @click="handleRender" :loading="rendering" class="w-full">
                      <el-icon><MagicStick /></el-icon> 生成提示词
                    </el-button>
                  </el-form-item>
                </el-form>

                <el-divider />

                <div v-if="renderedResult" class="render-result">
                  <div class="render-header">
                    <span class="render-label">生成结果</span>
                    <div class="render-actions">
                      <el-button size="small" text @click="copyContent(renderedResult)">
                        <el-icon><CopyDocument /></el-icon> 复制
                      </el-button>
                      <el-button size="small" text type="success" @click="handleUse">
                        <el-icon><Select /></el-icon> 使用 ({{ (prompt.usage_count) + (hasUsed ? 1 : 0) }})
                      </el-button>
                    </div>
                  </div>
                  <pre class="rendered-content">{{ renderedResult }}</pre>
                </div>
              </template>
            </el-card>
          </el-col>
        </el-row>
      </div>

      <!-- Loading State -->
      <div v-if="loading" v-loading="loading" class="loading-container" />

      <!-- Not Found -->
      <Transition name="fade-slide" appear>
        <div v-if="!prompt && !loading" class="not-found">
          <p>提示词不存在</p>
          <el-button @click="goBack">返回列表</el-button>
        </div>
      </Transition>
    </Transition>

    <!-- Version History Drawer -->
    <VersionHistoryPanel
      v-model="showVersionDrawer"
      :prompt-id="prompt?.id ?? null"
      @restored="handleVersionRestored"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft, Star, StarFilled, Edit, Delete, Clock,
  CopyDocument, MagicStick, Select,
} from '@element-plus/icons-vue'
import { usePromptsStore } from '../../stores/prompts'
import { renderTemplate } from '../../utils/render'
import VersionHistoryPanel from '../../components/prompts/VersionHistoryPanel.vue'

const router = useRouter()
const route = useRoute()
const promptsStore = usePromptsStore()

const loading = ref(true)
const rendering = ref(false)
const renderedResult = ref('')
const hasUsed = ref(false)
const livePreview = ref(false)
const showVersionDrawer = ref(false)
const selectedPresetId = ref<number | null>(null)
const variableValues = reactive<Record<string, string>>({})

const prompt = computed(() => promptsStore.currentPrompt)

const livePreviewResult = computed(() => {
  if (!livePreview.value || !prompt.value) return ''
  return renderTemplate(prompt.value.content || '', { ...variableValues })
})

async function loadPrompt(id: number) {
  loading.value = true
  try {
    await promptsStore.fetchPrompt(id)
    renderedResult.value = ''
    hasUsed.value = false
    Object.keys(variableValues).forEach((k) => delete variableValues[k])
    if (promptsStore.currentPrompt?.variables) {
      for (const v of promptsStore.currentPrompt.variables) {
        variableValues[v] = ''
      }
    }
  } catch {
    promptsStore.currentPrompt = null
  } finally {
    loading.value = false
  }
  try {
    await promptsStore.fetchPresets(id)
  } catch {
    // presets failure doesn't block main flow
  }
}

onMounted(() => {
  const id = Number(route.params.id)
  if (id) loadPrompt(id)
})

watch(() => route.params.id, (newId) => {
  if (newId) loadPrompt(Number(newId))
})

function goBack() {
  router.push('/prompts')
}

function editPrompt() {
  if (!prompt.value) return
  router.push(`/prompts/${prompt.value.id}/edit`)
}

async function deletePrompt() {
  if (!prompt.value) return
  try {
    await ElMessageBox.confirm('确定要删除这个提示词吗？', '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await promptsStore.deletePrompt(prompt.value.id)
    ElMessage.success('已删除')
    router.push('/prompts')
  } catch {}
}

async function toggleFav() {
  if (!prompt.value) return
  try {
    await promptsStore.toggleFavorite(prompt.value.id)
    ElMessage.success(prompt.value.is_favorite ? '已收藏' : '已取消收藏')
  } catch {
    ElMessage.error('操作失败')
  }
}

function handleVersionRestored() {
  showVersionDrawer.value = false
}

function handlePresetSelect(id: number | null) {
  if (!id) return
  const preset = promptsStore.presets.find((p) => p.id === id)
  if (!preset) return
  for (const [key, val] of Object.entries(preset.values)) {
    if (key in variableValues) {
      variableValues[key] = val
    }
  }
}

async function handleSavePreset() {
  const currentPrompt = prompt.value
  if (!currentPrompt) return
  const { value: name } = await ElMessageBox.prompt('请输入预设名称', '另存为预设', {
    inputPlaceholder: '例如：Python 开发环境',
    inputPattern: /\S+/,
    inputErrorMessage: '名称不能为空',
  })
  if (!name) return
  const values: Record<string, string> = {}
  for (const v of currentPrompt.variables || []) {
    if (variableValues[v]) values[v] = variableValues[v]
  }
  await promptsStore.createPreset(currentPrompt.id, name, values)
  ElMessage.success('预设已保存')
}

async function handleRender() {
  if (!prompt.value) return
  rendering.value = true
  try {
    const result = await promptsStore.renderPrompt(prompt.value.id, { ...variableValues })
    renderedResult.value = result.rendered_content
  } catch {
    ElMessage.error('渲染失败')
  } finally {
    rendering.value = false
  }
}

async function handleUse() {
  if (!prompt.value) return
  try {
    await promptsStore.recordUse(prompt.value.id)
    hasUsed.value = true
    ElMessage.success('已记录使用')
  } catch {
    ElMessage.error('记录失败')
  }
}

async function copyContent(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败')
  }
}
</script>

<style scoped>
.prompt-detail-page {
  padding: 28px 32px;
  max-width: 1200px;
  margin: 0 auto;
}

.loading-container {
  display: flex;
  justify-content: center;
  padding: 100px 0;
}

/* ── Header ── */

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 8px;
}

.detail-actions {
  display: flex;
  gap: 6px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* ── Section Cards ── */

.section-card {
  margin-bottom: 16px;
}

/* ── Title & Description ── */

.prompt-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--rh-text-primary);
  margin-bottom: 8px;
  line-height: 1.35;
}

.prompt-desc {
  font-size: 14px;
  color: var(--rh-text-secondary);
  margin-bottom: 12px;
  line-height: 1.6;
}

.usage-stats {
  font-size: 13px;
  color: var(--rh-text-tertiary);
  margin-bottom: 16px;
}

/* ── Tags ── */

.prompt-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.variables-display {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.vars-label {
  font-size: 13px;
  color: var(--rh-text-tertiary);
}

/* ── Template Content ── */

.template-content {
  background: var(--rh-bg-inset);
  padding: 18px 20px;
  border-radius: var(--rh-radius-sm);
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
  overflow-x: auto;
  margin-bottom: 16px;
  border: 1px solid var(--rh-border-faint);
}

/* ── No Variables ── */

.copy-btn {
  width: 100%;
  margin-top: 12px;
}

.no-vars {
  text-align: center;
  padding: 24px 0;
}

.no-vars p {
  color: var(--rh-text-tertiary);
  margin-bottom: 12px;
}

/* ── Live Preview ── */

.preview-toggle {
  margin-bottom: 12px;
}

.live-preview {
  margin-bottom: 16px;
  animation: fadeIn var(--rh-duration-normal) var(--rh-transition-normal) both;
}

.live-preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.live-preview-label {
  font-weight: 600;
  font-size: 13px;
  color: var(--rh-text-secondary);
}

.live-preview-content {
  background: var(--rh-primary-subtle);
  padding: 16px 18px;
  border-radius: var(--rh-radius-sm);
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
  overflow-x: auto;
  border: 1px solid var(--rh-primary-muted);
  color: var(--rh-primary-active);
}

/* ── Presets ── */

.presets-section {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.preset-select {
  width: 140px;
}

/* ── Render Result ── */

.render-result {
  animation: fadeIn var(--rh-duration-normal) var(--rh-transition-normal) both;
}

.render-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.render-label {
  font-weight: 600;
  font-size: 14px;
  color: var(--rh-text-primary);
}

.render-actions {
  display: flex;
  gap: 4px;
}

.rendered-content {
  background: rgba(5, 150, 105, 0.04);
  padding: 18px 20px;
  border-radius: var(--rh-radius-sm);
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
  overflow-x: auto;
  border: 1px solid rgba(5, 150, 105, 0.15);
  color: var(--rh-success);
}

.w-full {
  width: 100%;
}

.not-found {
  text-align: center;
  padding: 100px 0;
  color: var(--rh-text-tertiary);
}

.not-found p {
  margin-bottom: 16px;
  font-size: 16px;
}
</style>

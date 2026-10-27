<template>
  <div class="rh-page rh-page--narrow">
    <!-- Page Transition -->
    <Transition name="fade-slide" appear>
      <div class="detail-state">
        <LoadingState v-if="loading" variant="detail" />
        <ErrorState v-else-if="error" @retry="retryLoad" />
        <EmptyState v-else-if="!prompt" :icon="Document" title="提示词不存在">
          <el-button @click="goBack">返回列表</el-button>
        </EmptyState>
        <div v-else class="page-wrapper animate-fade-in-up">
        <!-- Header -->
        <div class="detail-header">
          <el-button text @click="goBack">
            <el-icon><ArrowLeft /></el-icon> 返回列表
          </el-button>
          <div class="detail-actions">
            <el-button :aria-pressed="prompt.is_favorite" @click="toggleFav">
              <el-icon><StarFilled v-if="prompt.is_favorite" /><Star v-else /></el-icon>
              {{ prompt.is_favorite ? '已收藏' : '收藏' }}
            </el-button>
            <el-button @click="showVersionDrawer = true">
              <el-icon><Clock /></el-icon> 历史版本
            </el-button>
            <el-button @click="router.push(`/prompts/${prompt.id}/lab`)">
              <el-icon><DataAnalysis /></el-icon> 测试提示词
            </el-button>
            <el-button @click="togglePublish" :loading="publishing">
              <el-icon><Promotion /></el-icon>
              {{ prompt.visibility === 'public' ? '取消发布' : '发布到广场' }}
            </el-button>
            <el-button type="primary" @click="editPrompt">
              <el-icon><Edit /></el-icon> 编辑
            </el-button>
            <el-button type="danger" plain @click="deletePrompt">
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
                <span class="vars-label">需要填写的内容：</span>
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
                <span>填写内容</span>
              </template>

              <div v-if="!prompt.variables?.length" class="no-vars">
                <p>这个提示词不需要填写内容，可以直接复制使用。</p>
                <el-button type="primary" class="copy-btn" @click="copyContent(prompt.content || '')">
                  <el-icon><CopyDocument /></el-icon> 复制提示词
                </el-button>
              </div>

              <template v-else>
                <!-- 实时预览：默认折叠，点击标题行展开；面板由 aria-controls 关联 -->
                <div class="preview-toggle">
                  <button
                    type="button"
                    class="preview-toggle-btn"
                    :aria-expanded="livePreview"
                    aria-controls="live-preview-panel"
                    @click="livePreview = !livePreview"
                  >
                    <span class="preview-toggle-text">实时预览（填好内容后的效果）</span>
                    <el-icon
                      class="preview-toggle-icon"
                      :class="{ 'is-open': livePreview }"
                    >
                      <ArrowDown />
                    </el-icon>
                  </button>
                </div>

                <div v-show="livePreview" id="live-preview-panel">
                  <!-- Live Preview Result -->
                  <div v-if="livePreviewResult" class="live-preview">
                    <div class="live-preview-header">
                      <span class="live-preview-label">即时预览</span>
                      <el-button size="small" text @click="copyContent(livePreviewResult)">
                        <el-icon><CopyDocument /></el-icon> 复制
                      </el-button>
                    </div>
                    <pre class="live-preview-content">{{ livePreviewResult }}</pre>
                  </div>
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
                      :placeholder="`请输入 ${v} 的内容`"
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
      </div>
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
  ArrowLeft, ArrowDown, Star, StarFilled, Edit, Delete, Clock,
  CopyDocument, MagicStick, Select, Promotion, Document, DataAnalysis,
} from '@element-plus/icons-vue'
import { usePromptsStore } from '../../stores/prompts'
import { plazaApi } from '../../api/plaza'
import { renderTemplate } from '../../utils/render'
import VersionHistoryPanel from '../../components/prompts/VersionHistoryPanel.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import ErrorState from '../../components/common/ErrorState.vue'
import LoadingState from '../../components/common/LoadingState.vue'

const router = useRouter()
const route = useRoute()
const promptsStore = usePromptsStore()

const loading = ref(true)
/** 加载失败标记：用于呈现 ErrorState，而非把失败与"真的不存在"混为一谈 */
const error = ref(false)
const rendering = ref(false)
const renderedResult = ref('')
const hasUsed = ref(false)
const livePreview = ref(false)
const showVersionDrawer = ref(false)
const publishing = ref(false)
const selectedPresetId = ref<number | null>(null)
const variableValues = reactive<Record<string, string>>({})

const prompt = computed(() => promptsStore.currentPrompt)

const livePreviewResult = computed(() => {
  if (!livePreview.value || !prompt.value) return ''
  return renderTemplate(prompt.value.content || '', { ...variableValues })
})

async function loadPrompt(id: number) {
  loading.value = true
  error.value = false
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
    error.value = true
  } finally {
    loading.value = false
  }
  try {
    await promptsStore.fetchPresets(id)
  } catch {
    // presets failure doesn't block main flow
  }
}

/** 重试：按当前路由 id 重新拉取（供 ErrorState 使用） */
function retryLoad() {
  const id = Number(route.params.id)
  if (id) loadPrompt(id)
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

async function togglePublish() {
  if (!prompt.value) return
  publishing.value = true
  try {
    const isPublic = prompt.value.visibility === 'public'
    if (isPublic) {
      await plazaApi.unpublish('prompt', prompt.value.id)
      prompt.value.visibility = 'private'
      ElMessage.success('已从资源广场取消发布')
    } else {
      await plazaApi.publish('prompt', prompt.value.id)
      prompt.value.visibility = 'public'
      ElMessage.success('已发布到资源广场，团队成员可见')
    }
  } catch {
    ElMessage.error('操作失败')
  } finally {
    publishing.value = false
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
    ElMessage.error('生成失败，请稍后再试')
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
  font-family: var(--rh-font-display);
  font-size: 22px;
  font-weight: 500;
  letter-spacing: 0;
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

/* ── Live Preview（默认折叠，点击标题行展开） ── */

.preview-toggle {
  margin-bottom: 12px;
}

/* 折叠触发器：原生按钮，可聚焦，键盘 Enter/Space 可操作 */
.preview-toggle-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  margin-left: -8px;
  border: 0;
  border-radius: var(--rh-radius-xs);
  background: transparent;
  color: var(--rh-text-secondary);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: var(--rh-transition-all-fast);
}

.preview-toggle-btn:hover {
  background: var(--rh-bg-hover);
  color: var(--rh-text-primary);
}

.preview-toggle-btn:focus-visible {
  outline: 2px solid var(--rh-primary);
  outline-offset: 2px;
}

.preview-toggle-icon {
  font-size: 14px;
  transition: transform var(--rh-duration-fast) var(--rh-transition-fast);
}

.preview-toggle-icon.is-open {
  transform: rotate(180deg);
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
  background: var(--rh-bg-secondary);
  padding: 18px 20px;
  border-radius: var(--rh-radius-sm);
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
  overflow-x: auto;
  border: 1px solid var(--rh-border);
  color: var(--rh-text-primary);
}

.w-full {
  width: 100%;
}
</style>

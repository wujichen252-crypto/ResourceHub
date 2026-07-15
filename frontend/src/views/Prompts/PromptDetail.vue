<template>
  <div class="prompt-detail-page">
    <div v-if="loading" v-loading="loading" class="loading-container" />

    <template v-if="prompt && !loading">
      <div class="detail-header">
        <el-button text @click="goBack">
          <el-icon><ArrowLeft /></el-icon> 返回列表
        </el-button>
        <div class="detail-actions">
          <el-button @click="toggleFav">
            <el-icon><StarFilled v-if="prompt.is_favorite" /><Star v-else /></el-icon>
            {{ prompt.is_favorite ? '已收藏' : '收藏' }}
          </el-button>
          <el-button type="primary" @click="editPrompt">
            <el-icon><Edit /></el-icon> 编辑
          </el-button>
          <el-button type="danger" @click="deletePrompt">
            <el-icon><Delete /></el-icon> 删除
          </el-button>
        </div>
      </div>

      <el-row :gutter="16">
        <!-- Left: Template -->
        <el-col :xs="24" :lg="14">
          <el-card shadow="never">
            <template #header>
              <div class="section-header">
                <span>提示词模板</span>
                <el-tag v-if="prompt.category_name" size="small">{{ prompt.category_name }}</el-tag>
              </div>
            </template>

            <h2 class="prompt-title">{{ prompt.title }}</h2>
            <p v-if="prompt.description" class="prompt-desc">{{ prompt.description }}</p>

            <div class="usage-stats">
              <span>使用次数: {{ prompt.usage_count }}</span>
            </div>

            <pre class="template-content">{{ prompt.content }}</pre>

            <div v-if="prompt.variables?.length" class="variables-display">
              <span class="vars-label">变量:</span>
              <el-tag
                v-for="v in prompt.variables"
                :key="v"
                size="small"
                type="warning"
              ><span v-text="'{{' + v + '}}'"></span></el-tag>
            </div>
          </el-card>
        </el-col>

        <!-- Right: Render -->
        <el-col :xs="24" :lg="10">
          <el-card shadow="never">
            <template #header>
              <span>填充变量</span>
            </template>

            <div v-if="!prompt.variables?.length" class="no-vars">
              <p>该提示词没有变量，可以直接复制使用。</p>
              <el-button type="primary" class="copy-btn" @click="copyContent(prompt.content)">
                <el-icon><CopyDocument /></el-icon> 复制提示词
              </el-button>
            </div>

            <template v-else>
              <el-form label-position="top">
                <el-form-item
                  v-for="v in prompt.variables"
                  :key="v"
                  :label="'{{' + v + '}}'"
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
    </template>

    <div v-if="!prompt && !loading" class="not-found">
      <p>提示词不存在</p>
      <el-button @click="goBack">返回列表</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft, Star, StarFilled, Edit, Delete,
  CopyDocument, MagicStick, Select,
} from '@element-plus/icons-vue'
import { usePromptsStore } from '../../stores/prompts'

const router = useRouter()
const route = useRoute()
const promptsStore = usePromptsStore()

const loading = ref(true)
const rendering = ref(false)
const renderedResult = ref('')
const hasUsed = ref(false)
const variableValues = reactive<Record<string, string>>({})

const prompt = computed(() => promptsStore.currentPrompt)

async function loadPrompt(id: number) {
  loading.value = true
  try {
    await promptsStore.fetchPrompt(id)
    // Reset render state
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
  padding: 32px;
  max-width: 1200px;
  margin: 0 auto;
}

.loading-container {
  display: flex;
  justify-content: center;
  padding: 100px 0;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 8px;
}

.detail-actions {
  display: flex;
  gap: 8px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

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
  margin-bottom: 20px;
}

.template-content {
  background: var(--rh-bg-subtle);
  padding: 20px;
  border-radius: 10px;
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
  overflow-x: auto;
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

.copy-btn {
  width: 100%;
  margin-top: 12px;
}

.no-vars {
  text-align: center;
  padding: 32px 0;
}

.no-vars p {
  color: var(--rh-text-tertiary);
  margin-bottom: 12px;
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
  background: #f0fdf4;
  padding: 20px;
  border-radius: 10px;
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
  overflow-x: auto;
  border: 1px solid #bbf7d0;
  color: #166534;
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

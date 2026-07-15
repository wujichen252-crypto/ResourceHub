<template>
  <div class="prompt-editor-page">
    <div class="editor-header">
      <div class="editor-header-left">
        <el-button text @click="goBack">
          <el-icon><ArrowLeft /></el-icon> 返回
        </el-button>
        <h1 class="editor-title">{{ isNew ? '新建提示词' : '编辑提示词' }}</h1>
      </div>
      <div class="editor-actions">
        <el-button @click="goBack">取消</el-button>
        <el-button type="primary" @click="savePrompt" :loading="saving">
          <el-icon><Check /></el-icon> 保存
        </el-button>
      </div>
    </div>

    <el-card shadow="never">
      <el-form :model="form" label-position="top">
        <el-row :gutter="16">
          <el-col :span="16">
            <el-form-item label="标题" required>
              <el-input v-model="form.title" placeholder="提示词标题" size="large" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="分类">
              <el-select v-model="form.category_id" placeholder="选择分类" clearable class="w-full">
                <el-option
                  v-for="cat in flatCategories"
                  :key="cat.id"
                  :label="cat.name"
                  :value="cat.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="描述">
          <el-input
            v-model="form.description"
            placeholder="简短描述这个提示词的用途"
            :rows="2"
            type="textarea"
          />
        </el-form-item>

        <el-form-item label="提示词内容" required>
          <template #label>
            <span>提示词内容 <el-tag size="small" type="warning">使用 <span v-text="'{{' + '变量名' + '}}'"></span> 添加占位符</el-tag></span>
          </template>
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="15"
            placeholder="请在此输入提示词模板...&#10;使用 {{变量名}} 语法添加可替换的变量占位符"
            class="content-input"
            @input="detectVariables"
          />
        </el-form-item>

        <el-form-item label="检测到的变量">
          <div class="detected-vars">
            <el-tag
              v-for="v in detectedVariables"
              :key="v"
              type="warning"
              class="var-tag"
              closable
              @close="removeVariable(v)"
            ><span v-text="'{{' + v + '}}'"></span></el-tag>
            <el-tag
              v-if="detectedVariables.length === 0"
              type="info"
              class="var-tag"
            >暂未检测到变量</el-tag>
          </div>
          <div class="add-var-row">
            <el-input
              v-model="newVariable"
              placeholder="添加变量名"
              class="add-var-input"
              size="small"
              @keyup.enter="addVariable"
            />
            <el-button size="small" @click="addVariable">添加</el-button>
          </div>
        </el-form-item>

        <el-form-item>
          <el-checkbox v-model="form.is_favorite">标记为收藏</el-checkbox>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Check } from '@element-plus/icons-vue'
import { usePromptsStore } from '../../stores/prompts'
import { useCategoriesStore } from '../../stores/categories'

const router = useRouter()
const route = useRoute()
const promptsStore = usePromptsStore()
const categoriesStore = useCategoriesStore()

const isNew = computed(() => route.params.id === 'new' || !route.params.id)
const saving = ref(false)
const newVariable = ref('')
const detectedVariables = ref<string[]>([])

const form = reactive({
  title: '',
  description: '',
  content: '',
  category_id: null as number | null,
  is_favorite: false,
})

const flatCategories = computed(() => {
  const flatten = (items: any[]): any[] => {
    const result: any[] = []
    for (const item of items) {
      result.push(item)
      if (item.children?.length) result.push(...flatten(item.children))
    }
    return result
  }
  return flatten(categoriesStore.promptCategories)
})

function detectVariables() {
  const matches = form.content.match(/\{\{(\w+)\}\}/g)
  if (matches) {
    const vars = [...new Set(matches.map((m: string) => m.replace(/\{\{|\}\}/g, '')))]
    // Merge with manually added variables, keep order
    const all = [...new Set([...detectedVariables.value, ...vars])]
    detectedVariables.value = all
  }
}

function addVariable() {
  const v = newVariable.value.trim()
  if (v && !detectedVariables.value.includes(v)) {
    detectedVariables.value.push(v)
  }
  newVariable.value = ''
}

function removeVariable(v: string) {
  detectedVariables.value = detectedVariables.value.filter((item) => item !== v)
}

onMounted(async () => {
  await categoriesStore.fetchCategories('prompt')

  if (!isNew.value) {
    const id = Number(route.params.id)
    try {
      await promptsStore.fetchPrompt(id)
      if (promptsStore.currentPrompt) {
        form.title = promptsStore.currentPrompt.title
        form.description = promptsStore.currentPrompt.description || ''
        form.content = promptsStore.currentPrompt.content
        form.category_id = promptsStore.currentPrompt.category_id
        form.is_favorite = promptsStore.currentPrompt.is_favorite
        detectedVariables.value = [...(promptsStore.currentPrompt.variables || [])]
      }
    } catch {
      ElMessage.error('提示词不存在')
      router.push('/prompts')
    }
  }
})

function goBack() {
  router.push('/prompts')
}

async function savePrompt() {
  if (!form.title.trim()) {
    ElMessage.warning('请输入标题')
    return
  }
  if (!form.content.trim()) {
    ElMessage.warning('请输入提示词内容')
    return
  }

  saving.value = true
  try {
    const data = {
      title: form.title,
      description: form.description || undefined,
      content: form.content,
      category_id: form.category_id,
      variables: detectedVariables.value,
      is_favorite: form.is_favorite,
    }

    if (isNew.value) {
      await promptsStore.createPrompt(data)
      ElMessage.success('提示词创建成功')
    } else {
      await promptsStore.updatePrompt(Number(route.params.id), data)
      ElMessage.success('提示词已保存')
    }
    router.push('/prompts')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.prompt-editor-page {
  padding: 32px;
  max-width: 900px;
  margin: 0 auto;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 12px;
}

.editor-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.editor-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--rh-text-primary);
  margin: 0;
}

.editor-actions {
  display: flex;
  gap: 8px;
}

.w-full {
  width: 100%;
}

.content-input :deep(textarea) {
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 14px;
  line-height: 1.7;
}

.detected-vars {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.var-tag {
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 12px;
}

.add-var-row {
  display: flex;
  gap: 8px;
}

.add-var-input {
  width: 200px;
}
</style>

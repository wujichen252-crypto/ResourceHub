<template>
  <div class="note-editor-page">
    <div class="editor-header">
      <div class="editor-header-left">
        <el-button text @click="goBack">
          <el-icon><ArrowLeft /></el-icon> 返回
        </el-button>
        <h1 class="editor-title">{{ isNew ? '新建笔记' : '编辑笔记' }}</h1>
      </div>
      <div class="editor-actions">
        <span v-if="saving" class="save-status">保存中...</span>
        <span v-else-if="saved" class="save-status saved">已保存</span>
        <el-button @click="goBack">取消</el-button>
        <el-button type="primary" @click="saveNote" :loading="saving">
          <el-icon><Check /></el-icon> 保存
        </el-button>
      </div>
    </div>

    <el-row :gutter="16" class="editor-body">
      <!-- Left: Editor -->
      <el-col :xs="24" :lg="12">
        <el-card shadow="never" class="editor-card">
          <el-form :model="form" label-position="top">
            <el-form-item label="标题">
              <el-input v-model="form.title" placeholder="输入笔记标题..." size="large" />
            </el-form-item>

            <el-form-item label="分类">
              <el-select v-model="form.category_id" placeholder="选择分类" clearable class="w-full">
                <el-option
                  v-for="cat in categoriesStore.noteCategories"
                  :key="cat.id"
                  :label="cat.name"
                  :value="cat.id"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="标签（逗号分隔）">
              <el-input v-model="tagsInput" placeholder="vue, typescript, 前端" />
            </el-form-item>

            <el-form-item label="内容 (Markdown)">
              <el-input
                v-model="form.content"
                type="textarea"
                :rows="20"
                placeholder="在此书写 Markdown 内容..."
                class="markdown-input"
              />
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- Right: Preview -->
      <el-col :xs="24" :lg="12">
        <el-card shadow="never" class="preview-card">
          <template #header>
            <span>预览</span>
          </template>
          <div class="preview-content markdown-body" v-html="previewContent" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Check } from '@element-plus/icons-vue'
import MarkdownIt from 'markdown-it'
import { useNotesStore } from '../../stores/notes'
import { useCategoriesStore } from '../../stores/categories'

const router = useRouter()
const route = useRoute()
const notesStore = useNotesStore()
const categoriesStore = useCategoriesStore()

const md = new MarkdownIt({ html: true, linkify: true, typographer: true })

const isNew = computed(() => route.params.id === 'new' || !route.params.id)
const saving = ref(false)
const saved = ref(false)
const tagsInput = ref('')

const form = reactive({
  title: '',
  content: '',
  category_id: null as number | null,
})

const previewContent = computed(() => {
  return form.content ? md.render(form.content) : '<p class="preview-empty">输入内容后在此预览</p>'
})

onMounted(async () => {
  await categoriesStore.fetchCategories('note')

  if (!isNew.value) {
    const id = Number(route.params.id)
    try {
      await notesStore.fetchNote(id)
      if (notesStore.currentNote) {
        form.title = notesStore.currentNote.title
        form.content = notesStore.currentNote.content || ''
        form.category_id = notesStore.currentNote.category_id
        tagsInput.value = (notesStore.currentNote.tags || []).join(', ')
      }
    } catch {
      ElMessage.error('笔记不存在')
      router.push('/notes')
    }
  }
})

function goBack() {
  router.push('/notes')
}

async function saveNote() {
  if (!form.title.trim()) {
    ElMessage.warning('请输入标题')
    return
  }

  saving.value = true
  saved.value = false

  const tags = tagsInput.value
    .split(',')
    .map((t) => t.trim())
    .filter((t: string) => t)

  try {
    if (isNew.value) {
      await notesStore.createNote({
        title: form.title,
        content: form.content,
        category_id: form.category_id,
        tags,
      })
      ElMessage.success('笔记创建成功')
    } else {
      await notesStore.updateNote(Number(route.params.id), {
        title: form.title,
        content: form.content,
        category_id: form.category_id,
        tags,
      })
      ElMessage.success('笔记已保存')
    }
    saved.value = true
    router.push('/notes')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.note-editor-page {
  padding: 32px;
  max-width: 1400px;
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
  align-items: center;
  gap: 12px;
}

.save-status {
  font-size: 13px;
  color: var(--rh-text-tertiary);
}

.save-status.saved {
  color: #10b981;
}

.editor-body {
  min-height: 70vh;
}

.editor-card,
.preview-card {
  height: 100%;
}

.w-full {
  width: 100%;
}

.markdown-input :deep(textarea) {
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 14px;
  line-height: 1.7;
}

.preview-content {
  font-size: 15px;
  line-height: 1.85;
  color: var(--rh-text-primary);
  min-height: 500px;
}

.preview-content :deep(h1),
.preview-content :deep(h2) {
  margin-top: 24px;
  margin-bottom: 12px;
  border-bottom: 1px solid var(--rh-border-light);
  padding-bottom: 8px;
}

.preview-content :deep(p) {
  margin-bottom: 12px;
}

.preview-content :deep(code) {
  background: var(--rh-bg-subtle);
  padding: 2px 8px;
  border-radius: 4px;
  color: var(--rh-primary);
  font-size: 14px;
}

.preview-content :deep(pre) {
  background: #1c1917;
  padding: 16px;
  border-radius: 10px;
  overflow-x: auto;
}

.preview-content :deep(pre code) {
  background: none;
  color: #e7e5e4;
}

.preview-content :deep(blockquote) {
  border-left: 3px solid var(--rh-primary);
  padding-left: 16px;
  color: var(--rh-text-secondary);
  background: var(--rh-bg-subtle);
  border-radius: 0 8px 8px 0;
  margin: 16px 0;
}
</style>

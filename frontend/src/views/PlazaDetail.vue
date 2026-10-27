<template>
  <div class="rh-page rh-page--narrow">
    <!-- Loading -->
    <LoadingState v-if="loading" variant="detail" />

    <!-- Load Error -->
    <ErrorState v-else-if="error" @retry="load" />

    <!-- Empty / Unpublished -->
    <EmptyState
      v-else-if="!detail"
      :icon="DocumentDelete"
      title="该内容不存在或已被作者取消发布"
    >
      <el-button type="primary" @click="router.push('/plaza')">返回资源广场</el-button>
    </EmptyState>

    <!-- Content -->
    <div v-else class="detail-layout animate-fade-in-up">
      <div class="detail-main">
        <div class="detail-topbar">
          <el-button text @click="goBack">
            <el-icon><ArrowLeft /></el-icon> 返回广场
          </el-button>
          <el-button type="primary" size="small" :loading="forking" @click="handleFork">
            <el-icon><CopyDocument /></el-icon> 复制到我的库
          </el-button>
        </div>

        <div class="detail-type-row">
          <el-tag size="small" :type="detail.type === 'note' ? 'info' : 'warning'">
            {{ detail.type === 'note' ? '笔记' : '提示词' }}
          </el-tag>
          <span v-if="detail.forked_from" class="fork-source">
            源自 {{ detail.forked_from }}
          </span>
        </div>

        <h1 class="detail-title">{{ detail.title }}</h1>

        <div class="detail-meta">
          <span class="author">
            <el-avatar :size="26" :src="detail.author_avatar || undefined">
              {{ detail.author_username.charAt(0).toUpperCase() }}
            </el-avatar>
            @{{ detail.author_username }}
          </span>
          <span v-if="detail.published_at" class="meta-item">发布于 {{ formatDate(detail.published_at) }}</span>
          <span class="meta-item">更新于 {{ formatDate(detail.updated_at) }}</span>
          <span v-if="detail.type === 'prompt' && detail.usage_count !== null" class="meta-item">
            使用 {{ detail.usage_count }} 次
          </span>
        </div>

        <div v-if="detail.tags.length" class="detail-tags">
          <el-tag v-for="t in detail.tags" :key="t" size="small" type="info">{{ t }}</el-tag>
        </div>

        <p v-if="detail.description" class="detail-desc">{{ detail.description }}</p>

        <el-divider />

        <!-- 笔记：Markdown/HTML 渲染；提示词：模板文本按原样展示 -->
        <div v-if="detail.type === 'note'" class="detail-content rh-markdown" v-html="renderedContent" />
        <pre v-else class="detail-content detail-plain">{{ detail.content }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, CopyDocument, DocumentDelete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'
import { plazaApi } from '../api/plaza'
import type { PlazaContentType, PlazaDetail } from '../api/plaza'
import { usePlazaStore } from '../stores/plaza'
import { formatDateTime } from '../utils/format'
import EmptyState from '../components/common/EmptyState.vue'
import ErrorState from '../components/common/ErrorState.vue'
import LoadingState from '../components/common/LoadingState.vue'

const route = useRoute()
const router = useRouter()
const plazaStore = usePlazaStore()

const md = new MarkdownIt({ html: false, linkify: true, typographer: true })

const loading = ref(true)
const forking = ref(false)
const detail = ref<PlazaDetail | null>(null)
/** 加载失败标记：用于在页面上呈现 ErrorState 而非停在空白 */
const error = ref(false)

/** 判断内容是否为 HTML（TipTap 富文本编辑器产物），否则按 Markdown 处理 */
function isHtml(str: string): boolean {
  return /<[a-z][\s\S]*>/i.test(str)
}

/** 笔记正文：Markdown/HTML → 消毒后的 HTML */
const renderedContent = computed(() => {
  const raw = detail.value?.content || ''
  const html = isHtml(raw) ? raw : md.render(raw)
  return DOMPurify.sanitize(html)
})

function validType(val: unknown): val is PlazaContentType {
  return val === 'note' || val === 'prompt'
}

/** 拉取详情：失败置 error 供 ErrorState 重试；非法参数走空态 */
async function load() {
  const type = route.params.type
  const id = Number(route.params.id)
  if (!validType(type) || !Number.isInteger(id) || id <= 0) {
    loading.value = false
    detail.value = null
    error.value = false
    return
  }
  loading.value = true
  error.value = false
  try {
    detail.value = await plazaApi.detail(type, id)
  } catch {
    detail.value = null
    error.value = true
  } finally {
    loading.value = false
  }
}

onMounted(load)

function formatDate(iso: string) {
  return formatDateTime(iso)
}

function goBack() {
  // 回到广场并切到对应类型标签
  if (detail.value) plazaStore.setType(detail.value.type)
  router.push('/plaza')
}

async function handleFork() {
  if (!detail.value) return
  const d = detail.value
  try {
    await ElMessageBox.confirm(
      `将「${d.title}」复制到你自己的库（来自 @${d.author_username}），副本独立可编辑。`,
      '复制到我的库',
      { confirmButtonText: '复制', cancelButtonText: '取消', type: 'info' },
    )
  } catch {
    return // 用户取消
  }
  forking.value = true
  try {
    const result = await plazaStore.fork(d.type, d.id)
    ElMessage.success(`已复制，来自 @${d.author_username}`)
    router.push(d.type === 'note' ? '/notes' : `/prompts/${result.id}`)
  } catch {
    ElMessage.error('复制失败，请稍后重试')
  } finally {
    forking.value = false
  }
}
</script>

<style scoped>
.detail-topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.detail-type-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.fork-source {
  font-size: 12px;
  color: var(--rh-text-tertiary);
}

.detail-title {
  font-family: var(--rh-font-display);
  font-size: 30px;
  font-weight: 500;
  color: var(--rh-text-primary);
  margin: 0 0 16px;
  line-height: 1.35;
  letter-spacing: 0;
}

.detail-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.author {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--rh-text-secondary);
}

.meta-item {
  font-size: 12.5px;
  color: var(--rh-text-tertiary);
}

.detail-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.detail-desc {
  font-size: 13.5px;
  color: var(--rh-text-secondary);
  margin: 0 0 4px;
}

.detail-content {
  font-size: 15.5px;
  line-height: 1.85;
  color: var(--rh-text-primary);
  word-break: break-word;
}

/* 提示词等纯文本内容保持原样展示 */
.detail-plain {
  background: var(--rh-bg-secondary);
  border: 1px solid var(--rh-border);
  border-radius: 10px;
  padding: 20px;
  font-size: 13.5px;
  line-height: 1.7;
  white-space: pre-wrap;
  font-family: inherit;
  margin: 0;
}

@media (max-width: 640px) {
  .detail-title {
    font-size: 24px;
  }
}
</style>

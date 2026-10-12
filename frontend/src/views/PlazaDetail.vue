<template>
  <div class="plaza-detail-page">
    <!-- Loading -->
    <div v-if="loading" class="center-state">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
    </div>

    <!-- Error / Unpublished -->
    <div v-else-if="!detail" class="center-state empty-state">
      <el-icon :size="48" color="var(--rh-text-tertiary)"><DocumentDelete /></el-icon>
      <p>该内容不存在或已被作者取消发布</p>
      <el-button type="primary" @click="router.push('/plaza')">返回资源广场</el-button>
    </div>

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
        <div v-if="detail.type === 'note'" class="detail-content" v-html="renderedContent" />
        <pre v-else class="detail-content detail-plain">{{ detail.content }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, CopyDocument, DocumentDelete, Loading } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'
import { plazaApi } from '../api/plaza'
import type { PlazaContentType, PlazaDetail } from '../api/plaza'
import { usePlazaStore } from '../stores/plaza'

const route = useRoute()
const router = useRouter()
const plazaStore = usePlazaStore()

const md = new MarkdownIt({ html: false, linkify: true, typographer: true })

const loading = ref(true)
const forking = ref(false)
const detail = ref<PlazaDetail | null>(null)

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

onMounted(async () => {
  const type = route.params.type
  const id = Number(route.params.id)
  if (!validType(type) || !Number.isInteger(id) || id <= 0) {
    loading.value = false
    return
  }
  try {
    detail.value = await plazaApi.detail(type, id)
  } catch {
    detail.value = null
  } finally {
    loading.value = false
  }
})

function formatDate(iso: string) {
  return new Date(iso).toLocaleString('zh-CN')
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
.plaza-detail-page {
  padding: 28px 32px;
  max-width: 960px;
  margin: 0 auto;
}

.center-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  min-height: 50vh;
  color: var(--rh-text-tertiary);
}

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
  font-size: 30px;
  font-weight: 700;
  color: var(--rh-text-primary);
  margin: 0 0 16px;
  line-height: 1.35;
  letter-spacing: -0.02em;
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
  background: var(--rh-bg-secondary, #f5f5f5);
  border: 1px solid var(--rh-border);
  border-radius: 10px;
  padding: 20px;
  font-size: 13.5px;
  line-height: 1.7;
  white-space: pre-wrap;
  font-family: inherit;
  margin: 0;
}

/* Markdown 渲染排版 */
.detail-content :deep(h1),
.detail-content :deep(h2),
.detail-content :deep(h3) {
  margin-top: 28px;
  margin-bottom: 12px;
  font-weight: 600;
}

.detail-content :deep(h1) {
  font-size: 24px;
  border-bottom: 1px solid var(--rh-border);
  padding-bottom: 8px;
}

.detail-content :deep(h2) {
  font-size: 20px;
  border-bottom: 1px solid var(--rh-border);
  padding-bottom: 6px;
}

.detail-content :deep(h3) {
  font-size: 17px;
}

.detail-content :deep(h1:first-child),
.detail-content :deep(h2:first-child),
.detail-content :deep(h3:first-child),
.detail-content :deep(p:first-child) {
  margin-top: 0;
}

.detail-content :deep(p) {
  margin-bottom: 16px;
}

.detail-content :deep(ul),
.detail-content :deep(ol) {
  margin: 0 0 16px;
  padding-left: 26px;
}

.detail-content :deep(li) {
  margin-bottom: 6px;
}

.detail-content :deep(code) {
  background: var(--rh-bg-subtle, rgba(0, 0, 0, 0.06));
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 14px;
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
}

.detail-content :deep(pre) {
  background: #1c1917;
  padding: 20px;
  border-radius: 10px;
  overflow-x: auto;
  margin: 20px 0;
}

.detail-content :deep(pre code) {
  background: none;
  padding: 0;
  color: #e7e5e4;
  font-size: 13.5px;
  line-height: 1.6;
}

.detail-content :deep(blockquote) {
  border-left: 3px solid var(--rh-primary);
  padding: 4px 0 4px 20px;
  color: var(--rh-text-secondary);
  margin: 20px 0;
  background: var(--rh-bg-subtle, rgba(0, 0, 0, 0.03));
  border-radius: 0 8px 8px 0;
}

.detail-content :deep(a) {
  color: var(--rh-primary);
  text-decoration: underline;
}

.detail-content :deep(img) {
  max-width: 100%;
  border-radius: 8px;
  margin: 16px 0;
}

.detail-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
}

.detail-content :deep(th),
.detail-content :deep(td) {
  border: 1px solid var(--rh-border);
  padding: 8px 12px;
  text-align: left;
  font-size: 14px;
}

.detail-content :deep(th) {
  background: var(--rh-bg-subtle, rgba(0, 0, 0, 0.04));
  font-weight: 600;
}

.detail-content :deep(hr) {
  border: none;
  border-top: 1px solid var(--rh-border);
  margin: 20px 0;
}

@media (max-width: 640px) {
  .plaza-detail-page {
    padding: 20px 16px;
  }

  .detail-title {
    font-size: 24px;
  }
}
</style>

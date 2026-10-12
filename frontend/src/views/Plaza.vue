<template>
  <div class="plaza-page">
    <!-- Page Header -->
    <Transition name="fade-slide" appear>
      <div class="page-header animate-fade-in-up">
        <div class="page-heading">
          <h1 class="page-title">资源广场</h1>
          <p class="page-subtitle">浏览社区成员公开发布的笔记与提示词，一键复制到自己的库</p>
        </div>
      </div>
    </Transition>

    <!-- Filter Bar -->
    <Transition name="fade-slide" appear>
      <div class="filter-bar animate-fade-in-up stagger-1">
        <el-radio-group v-model="currentType" @change="handleTypeChange">
          <el-radio-button value="note">笔记</el-radio-button>
          <el-radio-button value="prompt">提示词</el-radio-button>
        </el-radio-group>
        <el-input
          v-model="searchText"
          placeholder="搜索广场内容..."
          :prefix-icon="Search"
          clearable
          class="search-input"
          @input="handleSearch"
        />
        <span class="count-info">{{ plazaStore.total }} 个</span>
      </div>
    </Transition>

    <!-- Card Grid -->
    <div v-loading="plazaStore.loading" class="plaza-grid">
      <TransitionGroup name="stagger-grid" tag="div" class="grid-inner">
        <div
          v-for="(item, idx) in plazaStore.items"
          :key="`${item.type}-${item.id}`"
          class="grid-col"
          :class="'stagger-' + Math.min(idx, 5)"
        >
          <el-card shadow="never" class="plaza-card" @click="goDetail(item)">
            <div class="card-header">
              <el-tag size="small" :type="item.type === 'note' ? 'info' : 'warning'">
                {{ item.type === 'note' ? '笔记' : '提示词' }}
              </el-tag>
              <h3 class="card-title">{{ item.title }}</h3>
            </div>
            <p class="card-preview">{{ item.content_preview || '暂无内容' }}</p>
            <div class="card-tags" v-if="item.tags.length">
              <el-tag v-for="t in item.tags.slice(0, 4)" :key="t" size="small" class="tag-item">{{ t }}</el-tag>
            </div>
            <div class="card-footer">
              <span class="author">
                <el-avatar :size="20" :src="item.author_avatar || undefined">
                  {{ item.author_username.charAt(0).toUpperCase() }}
                </el-avatar>
                @{{ item.author_username }}
              </span>
              <el-button
                type="primary"
                size="small"
                plain
                @click.stop="handleFork(item)"
              >
                <el-icon><CopyDocument /></el-icon> 复制
              </el-button>
            </div>
          </el-card>
        </div>
      </TransitionGroup>
    </div>

    <!-- Empty State -->
    <div v-if="!plazaStore.loading && plazaStore.items.length === 0" class="empty-state">
      <p>广场还很安静，去发布你的第一篇内容吧</p>
      <el-button type="primary" @click="router.push(plazaStore.contentType === 'note' ? '/notes' : '/prompts')">
        去{{ plazaStore.contentType === 'note' ? '笔记库' : '提示词库' }}发布
      </el-button>
    </div>

    <!-- Pagination -->
    <div v-if="plazaStore.total > plazaStore.pageSize" class="pagination-wrapper">
      <el-pagination
        :current-page="plazaStore.page"
        :page-size="plazaStore.pageSize"
        :total="plazaStore.total"
        layout="prev, pager, next"
        @current-change="plazaStore.setPage"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { CopyDocument, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { PlazaContentType, PlazaItem } from '../api/plaza'
import { usePlazaStore } from '../stores/plaza'

const router = useRouter()
const plazaStore = usePlazaStore()

const searchText = ref('')
const currentType = ref<PlazaContentType>(plazaStore.contentType)
let searchTimer: ReturnType<typeof setTimeout> | null = null

onMounted(() => {
  plazaStore.fetchItems()
})

function handleTypeChange(val: string | number | boolean | undefined) {
  plazaStore.setType(val as PlazaContentType)
}

function handleSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    plazaStore.setSearch(searchText.value)
  }, 300)
}

/** 点击卡片跳转独立详情页 */
function goDetail(item: PlazaItem) {
  router.push(`/plaza/${item.type}/${item.id}`)
}

async function doFork(type: PlazaContentType, id: number, title: string, author: string) {
  try {
    await ElMessageBox.confirm(
      `将「${title}」复制到你自己的库（来自 @${author}），副本独立可编辑。`,
      '复制到我的库',
      { confirmButtonText: '复制', cancelButtonText: '取消', type: 'info' }
    )
  } catch {
    return // 用户取消
  }
  try {
    await plazaStore.fork(type, id)
    ElMessage.success(`已复制到你的${type === 'note' ? '笔记库' : '提示词库'}，来自 @${author}`)
  } catch {
    ElMessage.error('复制失败，请稍后重试')
  }
}

function handleFork(item: PlazaItem) {
  doFork(item.type, item.id, item.title, item.author_username)
}
</script>

<style scoped>
.plaza-page {
  padding: 28px 32px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 20px;
}

.page-title {
  font-size: 26px;
  font-weight: 700;
  color: var(--rh-text-primary);
  margin: 0;
  letter-spacing: -0.02em;
}

.page-subtitle {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--rh-text-tertiary);
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.search-input {
  max-width: 320px;
}

.count-info {
  margin-left: auto;
  font-size: 13px;
  color: var(--rh-text-tertiary);
}

.grid-inner {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.grid-col {
  flex: 1 1 calc(33.333% - 11px);
  min-width: 280px;
}

.plaza-card {
  height: 100%;
  cursor: pointer;
  border: 1px solid var(--rh-border);
  border-radius: 12px;
  transition: border-color 0.2s, transform 0.2s;
}

.plaza-card:hover {
  border-color: var(--rh-primary);
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--rh-text-primary);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-preview {
  font-size: 13px;
  color: var(--rh-text-secondary);
  line-height: 1.6;
  margin: 0 0 12px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 60px;
}

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 10px;
  border-top: 1px solid var(--rh-border);
}

.author {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--rh-text-tertiary);
}

.empty-state {
  text-align: center;
  padding: 60px 0;
  color: var(--rh-text-tertiary);
}

.empty-state p {
  margin-bottom: 16px;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}

@media (max-width: 900px) {
  .grid-col {
    flex-basis: calc(50% - 8px);
  }
}

@media (max-width: 640px) {
  .grid-col {
    flex-basis: 100%;
  }

  .filter-bar {
    flex-wrap: wrap;
  }
}
</style>

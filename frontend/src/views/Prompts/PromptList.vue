<template>
  <div class="rh-page">
    <!-- Page Header -->
    <Transition name="fade-slide" appear>
      <div class="page-header animate-fade-in-up">
        <div class="page-heading">
          <h1 class="page-title">提示词库</h1>
        </div>
        <div class="page-actions">
          <el-button @click="showAnalytics = true">
            <el-icon><DataAnalysis /></el-icon> 用量分析
          </el-button>
          <el-button type="primary" @click="createPrompt">
            <el-icon><Plus /></el-icon> 新建提示词
          </el-button>
        </div>
      </div>
    </Transition>

    <!-- Filter Bar — no card container, just a clean row -->
    <Transition name="fade-slide" appear>
      <div class="filter-bar animate-fade-in-up stagger-1">
        <div class="filter-row">
          <div class="filter-section search-section">
            <el-input
              ref="searchInputRef"
              v-model="searchText"
              placeholder="搜索提示词..."
              :prefix-icon="Search"
              clearable
              @input="handleSearch"
              class="filter-input"
            />
          </div>

          <div class="filter-section filter-col">
            <el-select
              v-model="selectedCategory"
              placeholder="分类"
              clearable
              class="filter-select"
              @change="handleCategoryChange"
            >
              <el-option label="全部分类" :value="null" />
              <el-option
                v-for="cat in flatCategories"
                :key="cat.id"
                :label="cat.name"
                :value="cat.id"
              />
            </el-select>
            <el-tooltip content="新建分类" placement="top">
              <el-button link size="small" aria-label="新建分类" @click="showNewCategoryDialog = true">
                <el-icon><Plus /></el-icon>
              </el-button>
            </el-tooltip>
          </div>

          <div class="filter-section filter-col">
            <el-select
              v-model="selectedTag"
              placeholder="标签"
              clearable
              class="filter-select"
              @change="handleTagChange"
            >
              <el-option label="全部标签" :value="null" />
              <el-option
                v-for="tag in allTags"
                :key="tag"
                :label="tag"
                :value="tag"
              />
            </el-select>
          </div>

          <div class="filter-section filter-col">
            <el-switch
              v-model="promptsStore.showFavoritesOnly"
              active-text="仅收藏"
              @change="handleFavoritesChange"
            />
          </div>

          <div class="filter-section count-section">
            {{ promptsStore.total }} 条
          </div>
          <div class="filter-section" v-if="hasActiveFilters">
            <el-button link size="small" @click="clearAllFilters">
              <el-icon><RefreshLeft /></el-icon> 清除筛选
            </el-button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 提示词卡片网格（CSS Grid，与广场页共用同一套响应式断点） -->
    <LoadingState v-if="promptsStore.loading" variant="card" />

    <TransitionGroup v-else name="stagger-grid" tag="div" class="prompt-grid">
      <div v-for="(prompt, idx) in promptsStore.prompts" :key="prompt.id" :class="'prompt-col stagger-' + Math.min(idx, 5)">
        <el-card shadow="never" class="prompt-card" @click="goToPrompt(prompt.id)">
          <div class="prompt-card-header">
            <h3 class="prompt-card-title">{{ prompt.title }}</h3>
            <button
              type="button"
              class="fav-icon"
              :class="{ favorited: prompt.is_favorite }"
              :aria-label="prompt.is_favorite ? `取消收藏「${prompt.title}」` : `收藏「${prompt.title}」`"
              :aria-pressed="prompt.is_favorite"
              @click.stop="toggleFav(prompt)"
            >
              <el-icon><StarFilled v-if="prompt.is_favorite" /><Star v-else /></el-icon>
            </button>
          </div>
          <p class="prompt-card-desc">{{ prompt.description || '暂无描述' }}</p>
          <div class="prompt-card-footer">
            <el-tag v-if="prompt.category_name" size="small" type="info">
              {{ prompt.category_name }}
            </el-tag>
            <span class="usage-badge">使用 {{ prompt.usage_count }} 次</span>
          </div>
          <div class="prompt-vars" v-if="prompt.variables?.length">
            <el-tag
              v-for="v in prompt.variables"
              :key="v"
              size="small"
              type="warning"
              class="var-tag"
            >{{ v }}</el-tag>
          </div>
        </el-card>
      </div>
    </TransitionGroup>

    <!-- Empty State -->
    <Transition name="fade" appear>
      <EmptyState
        v-if="!promptsStore.loading && promptsStore.prompts.length === 0"
        :icon="Document"
        title="还没有提示词"
      >
        <el-button type="primary" @click="createPrompt">创建第一个提示词</el-button>
      </EmptyState>
    </Transition>

    <!-- Pagination -->
    <div v-if="promptsStore.total > promptsStore.pageSize" class="pagination-wrapper">
      <el-pagination
        :current-page="promptsStore.page"
        :page-size="promptsStore.pageSize"
        :total="promptsStore.total"
        layout="prev, pager, next"
        @current-change="handlePageChange"
      />
    </div>
  </div>

  <!-- Usage Analytics Dialog -->
  <UsageAnalyticsPanel v-model="showAnalytics" />

  <!-- New Category Dialog -->
  <Transition name="scaleIn" appear>
    <el-dialog v-model="showNewCategoryDialog" title="新建分类" width="360px" :close-on-click-modal="false">
      <el-form label-position="top" @keyup.enter="handleCreateCategory">
        <el-form-item label="分类名称">
          <el-input v-model="newCategoryName" placeholder="请输入分类名称" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="creatingCategory" @click="handleCreateCategory">创建</el-button>
        </el-form-item>
      </el-form>
    </el-dialog>
  </Transition>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Document, Plus, RefreshLeft, Search, Star, StarFilled, DataAnalysis } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { InputInstance } from 'element-plus'
import { usePromptsStore } from '../../stores/prompts'
import { useCategoriesStore } from '../../stores/categories'
import type { Prompt } from '../../api/prompts'
import UsageAnalyticsPanel from '../../components/prompts/UsageAnalyticsPanel.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import LoadingState from '../../components/common/LoadingState.vue'

const route = useRoute()
const router = useRouter()
const promptsStore = usePromptsStore()
const categoriesStore = useCategoriesStore()

const searchText = ref('')
const selectedCategory = ref<number | null>(null)
const selectedTag = ref<string | null>(null)
const showAnalytics = ref(false)
const showNewCategoryDialog = ref(false)
const newCategoryName = ref('')
const creatingCategory = ref(false)
const searchInputRef = ref<InputInstance>()
let searchTimer: ReturnType<typeof setTimeout> | null = null

/** 是否存在生效中的筛选条件（用于展示「清除筛选」入口） */
const hasActiveFilters = computed(() => Boolean(searchText.value || selectedCategory.value !== null || selectedTag.value || promptsStore.showFavoritesOnly))

const allTags = computed(() => {
  const tagSet = new Set<string>()
  for (const p of promptsStore.prompts) {
    for (const t of p.tags || []) tagSet.add(t)
  }
  return [...tagSet].sort()
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

/** 筛选状态写入 URL：刷新、分享链接、浏览器后退都能还原 */
function syncQuery() {
  const query: Record<string, string> = {}
  if (searchText.value) query.q = searchText.value
  if (selectedCategory.value !== null) query.category = String(selectedCategory.value)
  if (selectedTag.value) query.tag = selectedTag.value
  if (promptsStore.showFavoritesOnly) query.fav = '1'
  router.replace({ query })
}

/** 从 URL 还原筛选状态 */
function restoreFromQuery() {
  const q = route.query
  if (typeof q.q === 'string') { searchText.value = q.q; promptsStore.setSearch(q.q) }
  if (typeof q.category === 'string' && !Number.isNaN(Number(q.category))) {
    selectedCategory.value = Number(q.category)
    promptsStore.setCategory(Number(q.category))
  }
  if (typeof q.tag === 'string') { selectedTag.value = q.tag; promptsStore.setTag(q.tag) }
  if (q.fav === '1') promptsStore.showFavoritesOnly = true
}

onMounted(async () => {
  restoreFromQuery()
  promptsStore.fetchPrompts()
  categoriesStore.fetchCategories('prompt')
  // 从工作台「搜索提示词」入口进入时自动聚焦搜索框
  if (route.query.focus === 'search') {
    await nextTick()
    searchInputRef.value?.focus()
  }
})

function handleSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    promptsStore.setSearch(searchText.value)
    syncQuery()
  }, 300)
}

function handleCategoryChange(val: number | null) {
  selectedCategory.value = val
  promptsStore.setCategory(val)
  syncQuery()
}

function handleTagChange(val: string | null) {
  selectedTag.value = val
  promptsStore.setTag(val)
  syncQuery()
}

function handleFavoritesChange() {
  promptsStore.toggleFavoritesOnly()
  syncQuery()
}

/** 一键复位全部筛选条件 */
function clearAllFilters() {
  searchText.value = ''
  selectedCategory.value = null
  selectedTag.value = null
  promptsStore.showFavoritesOnly = false
  promptsStore.setSearch('')
  promptsStore.setCategory(null)
  promptsStore.setTag(null)
  syncQuery()
}

function handlePageChange(page: number) {
  promptsStore.setPage(page)
}

function goToPrompt(id: number) {
  router.push(`/prompts/${id}`)
}

function createPrompt() {
  router.push('/prompts/new')
}

async function toggleFav(prompt: Prompt) {
  try {
    await promptsStore.toggleFavorite(prompt.id)
  } catch {
    ElMessage.error('操作失败')
  }
}

async function handleCreateCategory() {
  if (!newCategoryName.value.trim()) {
    ElMessage.warning('请输入分类名称')
    return
  }
  creatingCategory.value = true
  try {
    await categoriesStore.createCategory({
      name: newCategoryName.value.trim(),
      type: 'prompt',
    })
    ElMessage.success('分类创建成功')
    showNewCategoryDialog.value = false
    newCategoryName.value = ''
    await categoriesStore.fetchCategories('prompt')
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail?.message || '创建失败')
  } finally {
    creatingCategory.value = false
  }
}
</script>

<style scoped>
/* ── Page Header ── */

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.page-heading {
  flex: 1;
}

.page-title {
  font-family: var(--rh-font-display);
  font-size: 26px;
  font-weight: 500;
  color: var(--rh-text-primary);
  margin: 0;
  letter-spacing: 0;
}

/* 顶部动作用 flex 排列：两个动作相互独立，不使用按钮组（按钮组表示同一控件的选项） */
.page-actions {
  display: flex;
  gap: 8px;
}

/* ── Filter Bar ── */

.filter-bar {
  margin-bottom: 20px;
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--rh-bg-card);
  border: 1px solid var(--rh-border);
  border-radius: var(--rh-radius-sm);
  transition: border-color var(--rh-duration-normal) var(--rh-transition-normal);
}

.filter-section {
  display: flex;
  align-items: center;
}

.search-section {
  flex: 1 1 200px;
  min-width: 160px;
}

.filter-col {
  flex: 0 0 auto;
}

.count-section {
  font-size: 13px;
  color: var(--rh-text-tertiary);
  white-space: nowrap;
}

.filter-select {
  width: 120px;
}

/* ── Prompt Grid ── */

.prompt-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
  /* 行高由卡片内容决定、顶部对齐；原先的 min-height: 40vh 会把仅有的几行拉伸填满，
     导致卡片本体被拉高、下方出现大片空白 */
  align-content: start;
}

.prompt-col {
  min-width: 0;
}

.prompt-card {
  cursor: pointer;
  height: 100%;
  display: flex;
  flex-direction: column;
  transition: var(--rh-transition-all-normal);
}

/* 悬停位移全站统一为 translateY(-2px)，不再使用缩放 */
.prompt-card:hover {
  border-color: var(--rh-primary-muted);
  transform: translateY(-2px);
}

.prompt-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
  gap: 8px;
}

.prompt-card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--rh-text-primary);
  margin: 0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.4;
}

/* 收藏：真实按钮，保证键盘可达与触屏点击区 */
.fav-icon {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 32px;
  height: 32px;
  margin: -6px -6px 0 0;
  padding: 0;
  border: 0;
  border-radius: var(--rh-radius-xs);
  background: transparent;
  color: var(--rh-text-tertiary);
  cursor: pointer;
  transition: var(--rh-transition-all-fast);
}

.fav-icon .el-icon {
  font-size: 18px;
}

.fav-icon:hover {
  background: var(--rh-bg-hover);
  color: var(--rh-favorite);
}

.fav-icon.favorited {
  color: var(--rh-favorite);
}

.prompt-card-desc {
  font-size: 13px;
  color: var(--rh-text-secondary);
  line-height: 1.5;
  margin-bottom: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  min-height: 20px;
}

.prompt-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.usage-badge {
  font-size: 12px;
  color: var(--rh-text-tertiary);
}

.prompt-vars {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.var-tag {
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 11px;
}

/* ── Transition Group Animations ── */

/* 卡片入场动画：延迟统一由 global.css 的 .stagger-* 提供（不再本地复制一套） */
.stagger-grid-enter-active {
  animation: fadeInUp var(--rh-duration-slow) var(--rh-transition-normal) both;
}

.stagger-grid-leave-active {
  animation: fadeIn var(--rh-duration-fast) var(--rh-transition-fast) both;
}

/* ── Fade Animation ── */

.fade-enter-active, .fade-leave-active {
  transition: opacity var(--rh-duration-normal) var(--rh-transition-normal);
}

.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

/* ── Pagination ── */

.pagination-wrapper {
  display: flex;
  justify-content: center;
  padding: 20px 0 8px;
  border-top: 1px solid var(--rh-border-faint);
  margin-top: 8px;
}
</style>

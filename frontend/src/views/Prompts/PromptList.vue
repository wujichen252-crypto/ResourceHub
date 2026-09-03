<template>
  <div class="prompt-list-page">
    <!-- Page Header -->
    <Transition name="fade-slide" appear>
      <div class="page-header animate-fade-in-up">
        <div class="page-heading">
          <h1 class="page-title">提示词库</h1>
        </div>
        <el-button-group>
          <el-button @click="showAnalytics = true">
            <el-icon><DataAnalysis /></el-icon> 用量分析
          </el-button>
          <el-button type="primary" @click="createPrompt">
            <el-icon><Plus /></el-icon> 新建提示词
          </el-button>
        </el-button-group>
      </div>
    </Transition>

    <!-- Filter Bar — no card container, just a clean row -->
    <Transition name="fade-slide" appear>
      <div class="filter-bar animate-fade-in-up stagger-1">
        <div class="filter-row">
          <div class="filter-section search-section">
            <el-input
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
            <el-button link size="small" @click="showNewCategoryDialog = true">
              <el-icon><Plus /></el-icon>
            </el-button>
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
            {{ promptsStore.total }} 个
          </div>
        </div>
      </div>
    </Transition>

    <!-- Prompt Grid with Staggered Entrance -->
    <TransitionGroup name="stagger-grid" tag="div" v-loading="promptsStore.loading" class="prompt-grid">
      <div v-for="(prompt, idx) in promptsStore.prompts" :key="prompt.id" :class="'prompt-col stagger-' + idx">
        <el-col :xs="24" :sm="12" :md="8" :lg="6">
        <el-card shadow="never" class="prompt-card" @click="goToPrompt(prompt.id)">
          <div class="prompt-card-header">
            <h3 class="prompt-card-title">{{ prompt.title }}</h3>
            <el-icon
              class="fav-icon"
              :class="{ favorited: prompt.is_favorite }"
              @click.stop="toggleFav(prompt)"
            >
              <StarFilled v-if="prompt.is_favorite" />
              <Star v-else />
            </el-icon>
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
        </el-col>
        </div>
      </TransitionGroup>

    <!-- Empty State -->
    <Transition name="fade" appear>
      <div v-if="!promptsStore.loading && promptsStore.prompts.length === 0" class="empty-state">
        <p>还没有提示词</p>
        <el-button type="primary" @click="createPrompt">创建第一个提示词</el-button>
      </div>
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
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Search, Star, StarFilled, DataAnalysis } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { usePromptsStore } from '../../stores/prompts'
import { useCategoriesStore } from '../../stores/categories'
import type { Prompt } from '../../api/prompts'
import UsageAnalyticsPanel from '../../components/prompts/UsageAnalyticsPanel.vue'

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
let searchTimer: ReturnType<typeof setTimeout> | null = null

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

onMounted(() => {
  promptsStore.fetchPrompts()
  categoriesStore.fetchCategories('prompt')
})

function handleSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    promptsStore.setSearch(searchText.value)
  }, 300)
}

function handleCategoryChange(val: number | null) {
  promptsStore.setCategory(val)
}

function handleTagChange(val: string | null) {
  selectedTag.value = val
  promptsStore.setTag(val)
}

function handleFavoritesChange() {
  promptsStore.toggleFavoritesOnly()
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
.prompt-list-page {
  padding: 28px 32px;
  max-width: 1400px;
  margin: 0 auto;
}

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
  font-size: 26px;
  font-weight: 700;
  color: var(--rh-text-primary);
  margin: 0;
  letter-spacing: -0.02em;
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
  min-height: 40vh;
}

.prompt-col {
  margin-bottom: 16px;
}

.prompt-card {
  cursor: pointer;
  height: 100%;
  display: flex;
  flex-direction: column;
  transition: border-color var(--rh-duration-normal) var(--rh-transition-normal),
              transform var(--rh-duration-normal) var(--rh-transition-spring);
}

.prompt-card:hover {
  border-color: var(--rh-primary-muted);
  transform: scale(1.015);
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

.fav-icon {
  font-size: 18px;
  color: var(--rh-text-tertiary);
  cursor: pointer;
  flex-shrink: 0;
  transition: color var(--rh-duration-fast) var(--rh-transition-fast),
              transform var(--rh-duration-normal) var(--rh-transition-spring);
}

.fav-icon:hover {
  color: #eab308;
  transform: scale(1.2);
}

.fav-icon.favorited {
  color: #eab308;
}

.prompt-card-desc {
  font-size: 13px;
  color: var(--rh-text-secondary);
  line-height: 1.5;
  margin-bottom: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  min-height: 20px;
  flex: 1;
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

.stagger-grid-enter-active {
  animation: fadeInUp var(--rh-duration-slow) var(--rh-transition-normal) both;
}

.stagger-grid-leave-active {
  animation: fadeIn var(--rh-duration-fast) var(--rh-transition-fast) both;
}

.stagger-grid-enter-active.stagger-0 { animation-delay: 0ms; }
.stagger-grid-enter-active.stagger-1 { animation-delay: 40ms; }
.stagger-grid-enter-active.stagger-2 { animation-delay: 80ms; }
.stagger-grid-enter-active.stagger-3 { animation-delay: 120ms; }
.stagger-grid-enter-active.stagger-4 { animation-delay: 160ms; }
.stagger-grid-enter-active.stagger-5 { animation-delay: 200ms; }
.stagger-grid-enter-active.stagger-6 { animation-delay: 240ms; }
.stagger-grid-enter-active.stagger-7 { animation-delay: 280ms; }

/* ── Fade Animation ── */

.fade-enter-active, .fade-leave-active {
  transition: opacity var(--rh-duration-normal) var(--rh-transition-normal);
}

.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

/* ── Empty State ── */

.empty-state {
  text-align: center;
  padding: 80px 0;
  color: var(--rh-text-tertiary);
}

.empty-state p {
  margin-bottom: 16px;
  font-size: 16px;
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

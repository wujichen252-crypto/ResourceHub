<template>
  <div class="prompt-list-page">
    <div class="page-header">
      <div class="page-heading">
        <h1 class="page-title">提示词库</h1>
        <p class="page-desc">管理和复用你的 AI 提示词模板</p>
      </div>
      <el-button type="primary" @click="createPrompt">
        <el-icon><Plus /></el-icon> 新建提示词
      </el-button>
    </div>

    <!-- Filters -->
    <el-card shadow="never" class="filter-card">
      <el-row :gutter="12" align="middle">
        <el-col :xs="24" :sm="8">
          <el-input
            v-model="searchText"
            placeholder="搜索提示词..."
            :prefix-icon="Search"
            clearable
            @input="handleSearch"
          />
        </el-col>
        <el-col :xs="12" :sm="6">
          <el-select
            v-model="selectedCategory"
            placeholder="全部分类"
            clearable
            class="w-full"
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
        </el-col>
        <el-col :xs="12" :sm="4">
          <el-switch
            v-model="promptsStore.showFavoritesOnly"
            active-text="仅收藏"
            @change="handleFavoritesChange"
          />
        </el-col>
        <el-col :xs="24" :sm="6" class="stat-text">
          共 {{ promptsStore.total }} 个提示词
        </el-col>
      </el-row>
    </el-card>

    <!-- Prompt Grid -->
    <div v-loading="promptsStore.loading" class="prompt-grid">
      <el-row :gutter="16">
        <el-col
          v-for="prompt in promptsStore.prompts"
          :key="prompt.id"
          :xs="24" :sm="12" :md="8" :lg="6"
          class="prompt-col"
        >
          <el-card shadow="hover" class="prompt-card" @click="goToPrompt(prompt.id)">
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
            <div v-if="prompt.variables?.length" class="prompt-vars">
              <el-tag
                v-for="v in prompt.variables"
                :key="v"
                size="small"
                type="warning"
                class="var-tag"
              ><span v-text="'{{' + v + '}}'"></span></el-tag>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <div v-if="promptsStore.prompts.length === 0 && !promptsStore.loading" class="empty-state">
        <p>还没有提示词</p>
        <el-button type="primary" @click="createPrompt">创建第一个提示词</el-button>
      </div>
    </div>

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
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Search, Star, StarFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { usePromptsStore } from '../../stores/prompts'
import { useCategoriesStore } from '../../stores/categories'
import type { Prompt } from '../../api/prompts'

const router = useRouter()
const promptsStore = usePromptsStore()
const categoriesStore = useCategoriesStore()

const searchText = ref('')
const selectedCategory = ref<number | null>(null)
let searchTimer: ReturnType<typeof setTimeout> | null = null

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
</script>

<style scoped>
.prompt-list-page {
  padding: 32px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.page-heading {
  flex: 1;
}

.page-title {
  font-size: 26px;
  font-weight: 700;
  color: var(--rh-text-primary);
  margin: 0 0 4px;
}

.page-desc {
  font-size: 14px;
  color: var(--rh-text-tertiary);
  margin: 0;
}

/* ── Filter Bar ── */
.filter-card {
  margin-bottom: 24px;
}

.filter-card :deep(.el-card__body) {
  padding: 16px 20px;
}

.w-full {
  width: 100%;
}

.stat-text {
  font-size: 13px;
  color: var(--rh-text-tertiary);
  line-height: 32px;
  text-align: right;
}

/* ── Prompt Grid ── */
.prompt-grid {
  min-height: 40vh;
}

.prompt-col {
  margin-bottom: 20px;
}

.prompt-card {
  cursor: pointer;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.prompt-card:hover {
  transform: translateY(-3px);
}

.prompt-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
  gap: 8px;
}

.prompt-card-title {
  font-size: 16px;
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
  transition: var(--rh-transition);
}

.fav-icon:hover {
  transform: scale(1.15);
}

.fav-icon.favorited {
  color: #eab308;
}

.prompt-card-desc {
  font-size: 13px;
  color: var(--rh-text-secondary);
  line-height: 1.6;
  margin-bottom: 16px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  min-height: 41px;
  flex: 1;
}

.prompt-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
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
  padding: 24px 0 8px;
  border-top: 1px solid var(--rh-border-light);
  margin-top: 8px;
}
</style>

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { promptsApi } from '../api/prompts'
import type { Prompt, PromptCreate, PromptUpdate, RenderResponse } from '../api/prompts'

export const usePromptsStore = defineStore('prompts', () => {
  const prompts = ref<Prompt[]>([])
  const currentPrompt = ref<Prompt | null>(null)
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const selectedCategoryId = ref<number | null>(null)
  const showFavoritesOnly = ref(false)
  const searchQuery = ref('')
  const loading = ref(false)

  async function fetchPrompts() {
    loading.value = true
    try {
      const result = await promptsApi.list({
        page: page.value,
        page_size: pageSize.value,
        category_id: selectedCategoryId.value ?? undefined,
        is_favorite: showFavoritesOnly.value || undefined,
        search: searchQuery.value || undefined,
      })
      prompts.value = result.data
      total.value = result.total
    } finally {
      loading.value = false
    }
  }

  async function fetchPrompt(id: number) {
    currentPrompt.value = await promptsApi.get(id)
  }

  async function createPrompt(data: PromptCreate) {
    const prompt = await promptsApi.create(data)
    await fetchPrompts()
    return prompt
  }

  async function updatePrompt(id: number, data: PromptUpdate) {
    const prompt = await promptsApi.update(id, data)
    if (currentPrompt.value?.id === id) {
      currentPrompt.value = prompt
    }
    await fetchPrompts()
    return prompt
  }

  async function deletePrompt(id: number) {
    await promptsApi.delete(id)
    if (currentPrompt.value?.id === id) {
      currentPrompt.value = null
    }
    await fetchPrompts()
  }

  async function renderPrompt(id: number, variables: Record<string, string>): Promise<RenderResponse> {
    return promptsApi.render(id, variables)
  }

  async function recordUse(id: number) {
    const result = await promptsApi.recordUse(id)
    const p = prompts.value.find((item) => item.id === id)
    if (p) {
      p.usage_count = result.usage_count
    }
    if (currentPrompt.value?.id === id) {
      currentPrompt.value.usage_count = result.usage_count
    }
  }

  async function toggleFavorite(id: number) {
    const result = await promptsApi.toggleFavorite(id)
    const p = prompts.value.find((item) => item.id === id)
    if (p) {
      p.is_favorite = result.is_favorite
    }
    if (currentPrompt.value?.id === id) {
      currentPrompt.value.is_favorite = result.is_favorite
    }
    return result
  }

  function setCategory(id: number | null) {
    selectedCategoryId.value = id
    page.value = 1
    fetchPrompts()
  }

  function setSearch(query: string) {
    searchQuery.value = query
    page.value = 1
    fetchPrompts()
  }

  function toggleFavoritesOnly() {
    showFavoritesOnly.value = !showFavoritesOnly.value
    page.value = 1
    fetchPrompts()
  }

  function setPage(p: number) {
    page.value = p
    fetchPrompts()
  }

  return {
    prompts,
    currentPrompt,
    total,
    page,
    pageSize,
    selectedCategoryId,
    showFavoritesOnly,
    searchQuery,
    loading,
    fetchPrompts,
    fetchPrompt,
    createPrompt,
    updatePrompt,
    deletePrompt,
    renderPrompt,
    recordUse,
    toggleFavorite,
    setCategory,
    setSearch,
    toggleFavoritesOnly,
    setPage,
  }
})

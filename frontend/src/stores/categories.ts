import { defineStore } from 'pinia'
import { ref } from 'vue'
import { categoriesApi } from '../api/categories'
import type { CategoryTreeNode, CategoryCreate, CategoryUpdate } from '../api/categories'

export const useCategoriesStore = defineStore('categories', () => {
  const noteCategories = ref<CategoryTreeNode[]>([])
  const promptCategories = ref<CategoryTreeNode[]>([])
  const loading = ref(false)

  async function fetchCategories(type: 'note' | 'prompt') {
    loading.value = true
    try {
      const result = await categoriesApi.list(type)
      if (type === 'note') {
        noteCategories.value = result
      } else {
        promptCategories.value = result
      }
    } finally {
      loading.value = false
    }
  }

  async function createCategory(data: CategoryCreate) {
    const category = await categoriesApi.create(data)
    await fetchCategories(data.type)
    return category
  }

  async function updateCategory(id: number, data: CategoryUpdate, type: 'note' | 'prompt') {
    const category = await categoriesApi.update(id, data)
    await fetchCategories(type)
    return category
  }

  async function deleteCategory(id: number, type: 'note' | 'prompt') {
    await categoriesApi.delete(id)
    await fetchCategories(type)
  }

  return {
    noteCategories,
    promptCategories,
    loading,
    fetchCategories,
    createCategory,
    updateCategory,
    deleteCategory,
  }
})

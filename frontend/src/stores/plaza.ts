import { defineStore } from 'pinia'
import { ref } from 'vue'
import { plazaApi } from '../api/plaza'
import type { PlazaContentType, PlazaItem } from '../api/plaza'

export const usePlazaStore = defineStore('plaza', () => {
  const items = ref<PlazaItem[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const contentType = ref<PlazaContentType>('note')
  const searchQuery = ref('')
  const loading = ref(false)

  async function fetchItems() {
    loading.value = true
    try {
      const result = await plazaApi.list({
        type: contentType.value,
        page: page.value,
        page_size: pageSize.value,
        search: searchQuery.value || undefined,
      })
      items.value = result.items
      total.value = result.total
    } finally {
      loading.value = false
    }
  }

  function setType(type: PlazaContentType) {
    contentType.value = type
    page.value = 1
    fetchItems()
  }

  function setSearch(query: string) {
    searchQuery.value = query
    page.value = 1
    fetchItems()
  }

  function setPage(p: number) {
    page.value = p
    fetchItems()
  }

  // 复制广场内容到个人库，返回新副本 id
  async function fork(type: PlazaContentType, id: number) {
    return plazaApi.fork(type, id)
  }

  return {
    items,
    total,
    page,
    pageSize,
    contentType,
    searchQuery,
    loading,
    fetchItems,
    setType,
    setSearch,
    setPage,
    fork,
  }
})

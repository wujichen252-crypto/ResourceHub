import { defineStore } from 'pinia'
import { ref } from 'vue'
import { notesApi } from '../api/notes'
import type { Note, NoteCreate, NoteUpdate } from '../api/notes'

export const useNotesStore = defineStore('notes', () => {
  const notes = ref<Note[]>([])
  // 全量笔记（供左侧目录树渲染笔记叶子节点，不含正文）
  const allNotes = ref<Note[]>([])
  const currentNote = ref<Note | null>(null)
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const searchQuery = ref('')
  const selectedCategoryId = ref<number | null>(null)
  const selectedTag = ref<string | null>(null)
  const loading = ref(false)

  async function fetchNotes() {
    loading.value = true
    try {
      const result = await notesApi.list({
        page: page.value,
        page_size: pageSize.value,
        search: searchQuery.value || undefined,
        category_id: selectedCategoryId.value ?? undefined,
        tag: selectedTag.value ?? undefined,
      })
      notes.value = result.items
      total.value = result.total
    } finally {
      loading.value = false
    }
  }

  // 全量拉取（page_size 上限 100），供目录树渲染笔记叶子节点
  async function fetchAllNotes() {
    const result = await notesApi.list({ page: 1, page_size: 100 })
    allNotes.value = result.items
  }

  async function fetchNote(id: number) {
    currentNote.value = await notesApi.get(id)
  }

  async function createNote(data: NoteCreate) {
    const note = await notesApi.create(data)
    await fetchAllNotes()
    return note
  }

  async function updateNote(id: number, data: NoteUpdate) {
    const note = await notesApi.update(id, data)
    if (currentNote.value?.id === id) {
      currentNote.value = note
    }
    await fetchAllNotes()
    return note
  }

  async function deleteNote(id: number) {
    await notesApi.delete(id)
    if (currentNote.value?.id === id) {
      currentNote.value = null
    }
    allNotes.value = allNotes.value.filter((n) => n.id !== id)
  }

  async function togglePin(id: number) {
    const result = await notesApi.togglePin(id)
    const note = notes.value.find((n) => n.id === id)
    if (note) {
      note.is_pinned = result.is_pinned
    }
    const allNote = allNotes.value.find((n) => n.id === id)
    if (allNote) {
      allNote.is_pinned = result.is_pinned
    }
    if (currentNote.value?.id === id) {
      currentNote.value.is_pinned = result.is_pinned
    }
    return result
  }

  function setSearch(query: string) {
    searchQuery.value = query
    page.value = 1
    fetchNotes()
  }

  function setCategory(id: number | null) {
    selectedCategoryId.value = id
    selectedTag.value = null // 目录与标签过滤互斥
    page.value = 1
    fetchNotes()
  }

  // 标签过滤（Dashboard 标签云点击跳转 /notes 时使用）
  function setTag(tag: string | null) {
    selectedTag.value = tag
    selectedCategoryId.value = null
    page.value = 1
    fetchNotes()
  }

  function setPage(p: number) {
    page.value = p
    fetchNotes()
  }

  return {
    notes,
    allNotes,
    currentNote,
    total,
    page,
    pageSize,
    searchQuery,
    selectedCategoryId,
    selectedTag,
    loading,
    fetchNotes,
    fetchAllNotes,
    fetchNote,
    createNote,
    updateNote,
    deleteNote,
    togglePin,
    setSearch,
    setCategory,
    setTag,
    setPage,
  }
})

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { notesApi } from '../api/notes'
import type { Note, NoteCreate, NoteUpdate } from '../api/notes'

export const useNotesStore = defineStore('notes', () => {
  const notes = ref<Note[]>([])
  const currentNote = ref<Note | null>(null)
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const searchQuery = ref('')
  const selectedCategoryId = ref<number | null>(null)
  const loading = ref(false)

  async function fetchNotes() {
    loading.value = true
    try {
      const result = await notesApi.list({
        page: page.value,
        page_size: pageSize.value,
        search: searchQuery.value || undefined,
        category_id: selectedCategoryId.value ?? undefined,
      })
      notes.value = result.data
      total.value = result.total
    } finally {
      loading.value = false
    }
  }

  async function fetchNote(id: number) {
    currentNote.value = await notesApi.get(id)
  }

  async function createNote(data: NoteCreate) {
    const note = await notesApi.create(data)
    await fetchNotes()
    return note
  }

  async function updateNote(id: number, data: NoteUpdate) {
    const note = await notesApi.update(id, data)
    if (currentNote.value?.id === id) {
      currentNote.value = note
    }
    await fetchNotes()
    return note
  }

  async function deleteNote(id: number) {
    await notesApi.delete(id)
    if (currentNote.value?.id === id) {
      currentNote.value = null
    }
    await fetchNotes()
  }

  async function togglePin(id: number) {
    const result = await notesApi.togglePin(id)
    const note = notes.value.find((n) => n.id === id)
    if (note) {
      note.is_pinned = result.is_pinned
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
    page.value = 1
    fetchNotes()
  }

  function setPage(p: number) {
    page.value = p
    fetchNotes()
  }

  return {
    notes,
    currentNote,
    total,
    page,
    pageSize,
    searchQuery,
    selectedCategoryId,
    loading,
    fetchNotes,
    fetchNote,
    createNote,
    updateNote,
    deleteNote,
    togglePin,
    setSearch,
    setCategory,
    setPage,
  }
})

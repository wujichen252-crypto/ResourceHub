import http from './http'

export interface Note {
  id: number
  title: string
  content_preview?: string
  content?: string
  category_id: number | null
  category_name: string | null
  tags: string[]
  is_pinned: boolean
  created_at: string
  updated_at: string
}

export interface NoteCreate {
  title: string
  content?: string
  category_id?: number | null
  tags?: string[]
}

export interface NoteUpdate {
  title?: string
  content?: string
  category_id?: number | null
  tags?: string[]
}

export interface NoteListResponse {
  data: Note[]
  total: number
  page: number
  page_size: number
}

export interface NoteListParams {
  page?: number
  page_size?: number
  search?: string
  category_id?: number
  tag?: string
  is_pinned?: boolean
}

export const notesApi = {
  list(params?: NoteListParams): Promise<NoteListResponse> {
    return http.get('/notes', { params }).then((res) => res.data)
  },

  get(id: number): Promise<Note> {
    return http.get(`/notes/${id}`).then((res) => res.data.data)
  },

  create(data: NoteCreate): Promise<Note> {
    return http.post('/notes', data).then((res) => res.data.data)
  },

  update(id: number, data: NoteUpdate): Promise<Note> {
    return http.put(`/notes/${id}`, data).then((res) => res.data.data)
  },

  delete(id: number): Promise<void> {
    return http.delete(`/notes/${id}`)
  },

  togglePin(id: number): Promise<{ id: number; is_pinned: boolean }> {
    return http.put(`/notes/${id}/pin`).then((res) => res.data.data)
  },
}

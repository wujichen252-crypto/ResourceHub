import http, { LONG_TASK_TIMEOUT } from './http'

export interface Note {
  id: number
  title: string
  content_preview?: string
  content?: string
  content_format?: 'markdown' | 'json'
  content_json?: Record<string, any> | null
  category_id: number | null
  category_name: string | null
  tags: string[]
  is_pinned: boolean
  visibility?: 'private' | 'public'
  team_id?: number | null
  owner_username?: string | null
  source_username?: string | null
  created_at: string
  updated_at: string
}

export interface NoteCreate {
  title: string
  content?: string
  content_json?: Record<string, any> | null
  category_id?: number | null
  tags?: string[]
  /** 为空写个人空间，有值写入对应团队空间 */
  team_id?: number | null
}

export interface NoteUpdate {
  title?: string
  content?: string
  content_json?: Record<string, any> | null
  category_id?: number | null
  tags?: string[]
  team_id?: number | null
}

export interface NoteListResponse {
  items: Note[]
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
  /** 团队 ID：传值时查询该团队共享笔记 */
  team_id?: number
}

export interface MarkdownImportResult {
  created: number
  replaced: number
  skipped: { file: string; reason: string }[]
  total: number
}

export interface NoteBatchRequest {
  ids: number[]
  action: 'move' | 'tag' | 'delete'
  /** move：目标目录，null 表示移出目录 */
  category_id?: number | null
  /** tag：追加到现有标签之后（自动去重） */
  tags?: string[]
}

export const notesApi = {
  list(params?: NoteListParams): Promise<NoteListResponse> {
    return http.get('/notes', { params })
  },

  get(id: number): Promise<Note> {
    return http.get(`/notes/${id}`)
  },

  create(data: NoteCreate): Promise<Note> {
    return http.post('/notes', data)
  },

  importOrReplace(data: NoteCreate): Promise<Note> {
    return http.post('/notes/import', data)
  },

  update(id: number, data: NoteUpdate): Promise<Note> {
    return http.put(`/notes/${id}`, data)
  },

  delete(id: number): Promise<void> {
    return http.delete(`/notes/${id}`)
  },

  togglePin(id: number): Promise<{ id: number; is_pinned: boolean }> {
    return http.put(`/notes/${id}/pin`)
  },

  batch(data: NoteBatchRequest): Promise<{ affected: number }> {
    return http.post('/notes/batch', data)
  },

  exportMarkdown(): Promise<Blob> {
    return http.get('/notes/export/markdown', {
      responseType: 'blob',
      timeout: LONG_TASK_TIMEOUT,
    })
  },

  exportJson(): Promise<Blob> {
    return http.get('/notes/export/json', {
      responseType: 'blob',
      timeout: LONG_TASK_TIMEOUT,
    })
  },

  importMarkdown(files: File[]): Promise<MarkdownImportResult> {
    const form = new FormData()
    files.forEach((file) => form.append('files', file))
    return http.post('/notes/import/markdown', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: LONG_TASK_TIMEOUT,
    })
  },
}

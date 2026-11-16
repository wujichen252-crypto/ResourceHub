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

/** 反向链接条目（引用当前笔记的其他笔记） */
export interface NoteBacklink {
  id: number
  title: string
  updated_at: string
  /** 引用处上下文片段（引用所在段落/行），可能为空 */
  context?: string | null
}

/** 链接补全候选（个人 + 团队空间） */
export interface NoteCompletionItem {
  id: number
  title: string
  team_id: number | null
  team_name: string | null
}

/** 知识图谱节点 */
export interface GraphNode {
  id: number
  title: string
  team_id: number | null
  team_name: string | null
}

/** 知识图谱连线 */
export interface GraphLink {
  source: number
  target: number
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

  /** 反向链接：引用该笔记的其他笔记（按查看者可见性过滤） */
  backlinks(id: number): Promise<{ items: NoteBacklink[]; total: number }> {
    return http.get(`/notes/${id}/backlinks`)
  },

  /** 按标题解析笔记（点击双向链接跳转用）；未命中时后端返回 404 */
  resolveTitle(title: string, teamId?: number): Promise<{ id: number; title: string }> {
    return http.get('/notes/resolve', {
      params: { title, ...(teamId != null ? { team_id: teamId } : {}) },
    })
  },

  /** 链接补全候选：个人笔记 + 所在团队空间 */
  completion(q = '', limit = 8): Promise<{ items: NoteCompletionItem[] }> {
    return http.get('/notes/completion', { params: { q, limit } })
  },

  /** 知识图谱：节点与连线 */
  graph(): Promise<{ nodes: GraphNode[]; links: GraphLink[] }> {
    return http.get('/notes/graph')
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

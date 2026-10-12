import http from './http'

export type PlazaContentType = 'note' | 'prompt'

export interface PlazaItem {
  id: number
  type: PlazaContentType
  title: string
  content_preview: string
  tags: string[]
  author_username: string
  author_avatar: string | null
  published_at: string | null
  updated_at: string
  forked_from: string | null
}

export interface PlazaDetail {
  id: number
  type: PlazaContentType
  title: string
  description: string | null
  content: string
  tags: string[]
  variables: string[]
  author_id: number
  author_username: string
  author_avatar: string | null
  usage_count: number | null
  published_at: string | null
  created_at: string
  updated_at: string
  forked_from: string | null
}

export interface PlazaListResponse {
  items: PlazaItem[]
  total: number
  page: number
  page_size: number
}

export interface PlazaListParams {
  type: PlazaContentType
  page?: number
  page_size?: number
  search?: string
  tag?: string
}

export const plazaApi = {
  publish(type: PlazaContentType, id: number): Promise<{ id: number; visibility: string }> {
    return http.put('/plaza/publish', { type, id })
  },

  unpublish(type: PlazaContentType, id: number): Promise<{ id: number; visibility: string }> {
    return http.put('/plaza/unpublish', { type, id })
  },

  list(params: PlazaListParams): Promise<PlazaListResponse> {
    return http.get('/plaza/items', { params })
  },

  detail(type: PlazaContentType, id: number): Promise<PlazaDetail> {
    return http.get(`/plaza/items/${type}/${id}`)
  },

  fork(type: PlazaContentType, id: number): Promise<{ id: number; title: string }> {
    return http.post('/plaza/fork', { type, id })
  },

  mine(type?: PlazaContentType): Promise<{ items: PlazaItem[]; total: number }> {
    return http.get('/plaza/mine', { params: type ? { type } : {} })
  },
}

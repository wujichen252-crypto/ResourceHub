import http from './http'

export interface Prompt {
  id: number
  title: string
  description: string
  content?: string
  category_id: number | null
  category_name: string | null
  variables: string[]
  is_favorite: boolean
  usage_count: number
  created_at: string
  updated_at: string
}

export interface PromptCreate {
  title: string
  description?: string
  content: string
  category_id?: number | null
  variables?: string[]
}

export interface PromptUpdate {
  title?: string
  description?: string
  content?: string
  category_id?: number | null
  variables?: string[]
  is_favorite?: boolean
}

export interface PromptListResponse {
  data: Prompt[]
  total: number
  page: number
  page_size: number
}

export interface PromptListParams {
  page?: number
  page_size?: number
  category_id?: number
  is_favorite?: boolean
  search?: string
  sort_by?: string
}

export interface RenderResponse {
  id: number
  title: string
  original_content: string
  rendered_content: string
  variables: Record<string, string>
}

export const promptsApi = {
  list(params?: PromptListParams): Promise<PromptListResponse> {
    return http.get('/prompts', { params }).then((res) => res.data)
  },

  get(id: number): Promise<Prompt> {
    return http.get(`/prompts/${id}`).then((res) => res.data.data)
  },

  create(data: PromptCreate): Promise<Prompt> {
    return http.post('/prompts', data).then((res) => res.data.data)
  },

  update(id: number, data: PromptUpdate): Promise<Prompt> {
    return http.put(`/prompts/${id}`, data).then((res) => res.data.data)
  },

  delete(id: number): Promise<void> {
    return http.delete(`/prompts/${id}`)
  },

  render(id: number, variables: Record<string, string>): Promise<RenderResponse> {
    return http.post(`/prompts/${id}/render`, { variables }).then((res) => res.data.data)
  },

  recordUse(id: number): Promise<{ id: number; usage_count: number }> {
    return http.post(`/prompts/${id}/use`).then((res) => res.data.data)
  },

  toggleFavorite(id: number): Promise<{ id: number; is_favorite: boolean }> {
    return http.put(`/prompts/${id}/favorite`).then((res) => res.data.data)
  },
}

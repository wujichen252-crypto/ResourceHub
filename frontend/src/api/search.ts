import http from './http'

export type SearchResultType = 'note' | 'prompt'

export interface SearchResultItem {
  type: SearchResultType
  id: number
  title: string
  snippet: string
  category_name: string | null
  tags: string[]
  updated_at: string | null
}

export interface SearchResponse {
  query: string
  total: number
  items: SearchResultItem[]
}

export const searchApi = {
  search(q: string, limit = 5): Promise<SearchResponse> {
    return http.get('/search', { params: { q, limit } })
  },
}

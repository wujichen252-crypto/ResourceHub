import http from './http'

export interface CategoryTreeNode {
  id: number
  name: string
  type: string
  parent_id: number | null
  sort_order: number
  children: CategoryTreeNode[]
}

export interface CategoryCreate {
  name: string
  type: 'note' | 'prompt'
  parent_id?: number | null
  sort_order?: number
}

export interface CategoryUpdate {
  name?: string
  parent_id?: number | null
  sort_order?: number
}

export const categoriesApi = {
  list(type: 'note' | 'prompt'): Promise<CategoryTreeNode[]> {
    return http.get('/categories', { params: { type } })
  },

  create(data: CategoryCreate): Promise<any> {
    return http.post('/categories', data)
  },

  update(id: number, data: CategoryUpdate): Promise<any> {
    return http.put(`/categories/${id}`, data)
  },

  delete(id: number): Promise<void> {
    return http.delete(`/categories/${id}`)
  },
}

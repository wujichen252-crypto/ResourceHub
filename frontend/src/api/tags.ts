import http from './http'

export type TagScope = 'note' | 'prompt'

export interface TagCount {
  name: string
  count: number
}

export const tagsApi = {
  list(scope: TagScope): Promise<{ items: TagCount[] }> {
    return http.get('/tags', { params: { scope } })
  },

  rename(scope: TagScope, oldName: string, newName: string): Promise<{ updated: number }> {
    return http.post('/tags/rename', { scope, old_name: oldName, new_name: newName })
  },

  merge(scope: TagScope, sources: string[], target: string): Promise<{ updated: number }> {
    return http.post('/tags/merge', { scope, sources, target })
  },

  remove(scope: TagScope, name: string): Promise<{ updated: number }> {
    return http.delete('/tags', { params: { scope, name } })
  },
}

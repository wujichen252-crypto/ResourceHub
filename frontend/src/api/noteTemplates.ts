import http from './http'

export interface NoteTemplate {
  id: number
  name: string
  content: string
  content_format: 'markdown' | 'json'
  content_json: Record<string, any> | null
  tags: string[]
  category_id: number | null
  created_at: string
  updated_at: string
}

export interface NoteTemplateCreate {
  name: string
  content?: string
  content_json?: Record<string, any> | null
  tags?: string[]
  category_id?: number | null
}

export type NoteTemplateUpdate = Partial<NoteTemplateCreate>

export const noteTemplatesApi = {
  list(): Promise<{ items: NoteTemplate[] }> {
    return http.get('/note-templates')
  },

  create(data: NoteTemplateCreate): Promise<NoteTemplate> {
    return http.post('/note-templates', data)
  },

  update(id: number, data: NoteTemplateUpdate): Promise<NoteTemplate> {
    return http.put(`/note-templates/${id}`, data)
  },

  remove(id: number): Promise<void> {
    return http.delete(`/note-templates/${id}`)
  },
}

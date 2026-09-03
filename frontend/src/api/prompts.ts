import http from './http'

export interface Prompt {
  id: number
  title: string
  description: string
  content?: string
  category_id: number | null
  category_name: string | null
  variables: string[]
  tags: string[]
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
  tags?: string[]
}

export interface PromptUpdate {
  title?: string
  description?: string
  content?: string
  category_id?: number | null
  variables?: string[]
  tags?: string[]
  is_favorite?: boolean
}

export interface PromptListResponse {
  items: Prompt[]
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
  tag?: string
}

export interface RenderResponse {
  id: number
  title: string
  original_content: string
  rendered_content: string
  variables: Record<string, string>
}

export interface PromptVersion {
  id: number
  prompt_id: number
  version_number: number
  title: string
  description: string
  content: string
  variables: string[]
  tags: string[]
  message: string
  labels: string[]
  branch_name: string
  created_at: string
}

export interface DiffSegment {
  type: 'equal' | 'insert' | 'delete'
  value: string
}

export interface DiffResponse {
  v1: PromptVersion
  v2: PromptVersion
  diffs: DiffSegment[]
}

export interface PromptPreset {
  id: number
  prompt_id: number
  name: string
  values: Record<string, string>
  created_at: string
}

export interface UsageAnalytics {
  total_uses: number
  most_used: Array<{ prompt_id: number; title: string; count: number }>
  daily_usage: Array<{ date: string; count: number }>
}

export const promptsApi = {
  list(params?: PromptListParams): Promise<PromptListResponse> {
    return http.get('/prompts', { params })
  },

  get(id: number): Promise<Prompt> {
    return http.get(`/prompts/${id}`)
  },

  create(data: PromptCreate): Promise<Prompt> {
    return http.post('/prompts', data)
  },

  update(id: number, data: PromptUpdate): Promise<Prompt> {
    return http.put(`/prompts/${id}`, data)
  },

  delete(id: number): Promise<void> {
    return http.delete(`/prompts/${id}`)
  },

  render(id: number, variables: Record<string, string>): Promise<RenderResponse> {
    return http.post(`/prompts/${id}/render`, { variables })
  },

  recordUse(id: number): Promise<{ id: number; usage_count: number }> {
    return http.post(`/prompts/${id}/use`)
  },

  toggleFavorite(id: number): Promise<{ id: number; is_favorite: boolean }> {
    return http.put(`/prompts/${id}/favorite`)
  },

  // ── Version History ──
  getVersions(id: number): Promise<PromptVersion[]> {
    return http.get(`/prompts/${id}/versions`)
  },

  getVersion(id: number, versionId: number): Promise<PromptVersion> {
    return http.get(`/prompts/${id}/versions/${versionId}`)
  },

  restoreVersion(id: number, versionId: number): Promise<Prompt> {
    return http.post(`/prompts/${id}/versions/${versionId}/restore`)
  },

  // ── Presets ──
  getPresets(id: number): Promise<PromptPreset[]> {
    return http.get(`/prompts/${id}/presets`)
  },

  createPreset(id: number, data: { name: string; values: Record<string, string> }): Promise<PromptPreset> {
    return http.post(`/prompts/${id}/presets`, data)
  },

  deletePreset(presetId: number): Promise<void> {
    return http.delete(`/prompts/presets/${presetId}`)
  },

  // ── Analytics ──
  getUsageAnalytics(): Promise<UsageAnalytics> {
    return http.get('/prompts/analytics/usage')
  },

  // ── Diff ──
  diffVersions(id: number, versionId: number, targetVersionId: number): Promise<DiffResponse> {
    return http.get(`/prompts/${id}/versions/${versionId}/diff`, {
      params: { target_version_id: targetVersionId },
    })
  },

  // ── Labels ──
  updateLabels(id: number, versionId: number, labels: string[]): Promise<PromptVersion> {
    return http.put(`/prompts/${id}/versions/${versionId}/labels`, { labels })
  },
}

import http from './http'

/** 场景中文名（与后端 ai_usage_logs.scene 对应） */
export const sceneLabels: Record<string, string> = {
  chat: '对话问答',
  agent: '智能体',
  embedding: '向量化索引',
  eval: '提示词评测',
  optimize: '提示词优化',
  inline: '笔记内联',
  memory: '记忆抽取',
  proactive: '主动关怀',
}

/** 单个调用场景的成本与用量 */
export interface SceneCostItem {
  scene: string
  calls: number
  tokens: number
  cost: number
}

export interface ModelCostItem {
  model: string
  calls: number
  tokens: number
  cost: number
}

/** /api/roi/summary 响应 */
export interface RoiSummary {
  days: number
  total_tokens: number
  total_calls: number
  success_rate: number
  avg_latency_ms: number
  cost_total: number
  unpriced_tokens: number
  by_scene: SceneCostItem[]
  by_model: ModelCostItem[]
  quota_used_today: number
  quota_limit: number
}

/** /api/roi/trend 单日趋势点 */
export interface RoiTrendPoint {
  date: string
  calls: number
  tokens: number
  cost: number
  failures: number
  scenes: Record<string, number>
}

/** 笔记健康度分级 */
export type NoteGrade = 'high_yield' | 'normal' | 'sleeping' | 'cost_heavy' | 'unindexed'

export const gradeLabels: Record<NoteGrade, string> = {
  high_yield: '高产出',
  normal: '正常',
  sleeping: '沉睡',
  cost_heavy: '高耗低效',
  unindexed: '未索引',
}

/** /api/roi/notes 条目 */
export interface NoteRoiItem {
  note_id: number
  title: string
  citations: number
  index_tokens: number
  index_cost: number | null
  grade: NoteGrade
  roi_score: number
}

/** /api/roi/prompts 条目 */
export interface PromptRoiItem {
  prompt_id: number
  title: string
  usage_count: number
  quality_score: number | null
  optimize_tokens: number
  optimize_cost: number | null
  score_gain: number | null
  roi_score: number
}

/** /api/roi/scenes 散点条目 */
export interface SceneQuadrantPoint {
  scene: string
  calls: number
  tokens: number
  cost: number
  avg_latency_ms: number
}

export const roiApi = {
  summary(days: number): Promise<RoiSummary> {
    return http.get('/roi/summary', { params: { days } })
  },
  trend(days: number): Promise<{ days: number; points: RoiTrendPoint[] }> {
    return http.get('/roi/trend', { params: { days } })
  },
  notes(days: number): Promise<NoteRoiItem[]> {
    return http.get('/roi/notes', { params: { days } })
  },
  prompts(): Promise<PromptRoiItem[]> {
    return http.get('/roi/prompts')
  },
  scenes(days: number): Promise<SceneQuadrantPoint[]> {
    return http.get('/roi/scenes', { params: { days } })
  },
}

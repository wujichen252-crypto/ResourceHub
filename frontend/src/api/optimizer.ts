import http from './http'

/** 逐用例评测明细（与 eval.ts 的 EvalCaseResult 对齐，仅保留展示所需字段） */
export interface OptimizationCaseResult {
  case_id: number
  variables: Record<string, string>
  output: string
  score: number | null
  judge_reason: string | null
  latency_ms: number
  total_tokens: number
}

/** 一轮评测的完整明细（baseline_detail / candidate_detail） */
export interface OptimizationEvalDetail {
  suite_id: number
  case_count: number
  avg_score: number | null
  total_tokens: number
  results: OptimizationCaseResult[]
}

/** 优化会话状态：running 执行中 / awaiting_review 等人决策 / completed 已采纳 / cancelled 已放弃 / failed 失败 */
export type OptimizationRunStatus =
  | 'running'
  | 'awaiting_review'
  | 'completed'
  | 'cancelled'
  | 'failed'

/** 优化会话 */
export interface OptimizationRun {
  id: number
  prompt_id: number
  suite_id: number
  status: OptimizationRunStatus
  round_number: number
  max_rounds: number
  score_threshold: number
  baseline_version_id: number | null
  baseline_content: string | null
  baseline_score: number | null
  candidate_content: string | null
  candidate_score: number | null
  candidate_version_id: number | null
  analysis: string | null
  changelog: string | null
  total_tokens: number
  error_message: string | null
  baseline_detail: OptimizationEvalDetail | null
  candidate_detail: OptimizationEvalDetail | null
  created_at: string | null
  updated_at: string | null
}

/** 单轮历史记录 */
export interface OptimizationRound {
  id: number
  round_number: number
  status: 'completed' | 'skipped'
  candidate_content: string | null
  candidate_score: number | null
  reference_score: number | null
  analysis: string | null
  changelog: string | null
  snapshot: OptimizationEvalDetail | null
  total_tokens: number
  created_at: string | null
}

/** 发起优化的入参 */
export interface OptimizationStartRequest {
  prompt_id: number
  suite_id: number
  prompt_version_id?: number | null
  max_rounds?: number
  score_threshold?: number
  temperature?: number
}

/** 采纳后返回的落库版本信息 */
export interface AcceptedVersion {
  id: number
  version_number: number
  message: string
}

export const optimizerApi = {
  /** 发起自动优化会话并启动第一轮 */
  startRun(data: OptimizationStartRequest): Promise<OptimizationRun> {
    return http.post('/ai/prompt-optimizer/runs', data)
  },

  /** 会话列表（时间倒序，可按提示词过滤）；用于恢复进行中的会话 */
  listRuns(promptId?: number): Promise<{ items: OptimizationRun[] }> {
    return http.get('/ai/prompt-optimizer/runs', {
      params: promptId !== undefined ? { prompt_id: promptId } : undefined,
    })
  },

  /** 查询会话状态（轮询用） */
  getStatus(runId: number): Promise<OptimizationRun> {
    return http.get(`/ai/prompt-optimizer/runs/${runId}`)
  },

  /** 会话的轮次历史 */
  listRounds(runId: number): Promise<{ items: OptimizationRound[] }> {
    return http.get(`/ai/prompt-optimizer/runs/${runId}/rounds`)
  },

  /** 继续下一轮优化 */
  iterate(runId: number): Promise<OptimizationRun> {
    return http.post(`/ai/prompt-optimizer/runs/${runId}/iterate`)
  },

  /** 采纳候选：落新版本并更新正文 */
  accept(runId: number): Promise<OptimizationRun & { new_version: AcceptedVersion }> {
    return http.post(`/ai/prompt-optimizer/runs/${runId}/accept`)
  },

  /** 放弃会话 */
  cancel(runId: number): Promise<OptimizationRun> {
    return http.post(`/ai/prompt-optimizer/runs/${runId}/cancel`)
  },
}

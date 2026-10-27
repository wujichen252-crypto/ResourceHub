import http, { LONG_TASK_TIMEOUT } from './http'

/** 评测用例（后端已把 variables 反序列化为对象） */
export interface EvalCase {
  id: number
  variables: Record<string, string>
  expected_output: string | null
  rubric: string | null
}

/** 评测集 */
export interface EvalSuite {
  id: number
  prompt_id: number
  name: string
  description: string | null
  judge_model: string | null
  case_count: number
  created_at: string | null
  cases: EvalCase[]
}

/** 新建评测集的用例入参 */
export interface EvalCaseInput {
  variables: Record<string, string>
  expected_output?: string | null
  rubric?: string | null
}

/** 新建评测集入参 */
export interface EvalSuiteCreate {
  prompt_id: number
  name: string
  description?: string | null
  judge_model?: string | null
  cases: EvalCaseInput[]
}

/** 执行评测入参 */
export interface EvalRunRequest {
  model?: string
  prompt_version_id?: number | null
  temperature?: number
}

/** 单用例评测结果 */
export interface EvalCaseResult {
  case_id: number
  variables: Record<string, string>
  output: string
  score: number | null
  judge_reason: string | null
  latency_ms: number
  total_tokens: number
}

/** 一次评测的汇总结果 */
export interface EvalRunResult {
  suite_id: number
  prompt_id: number
  prompt_version_id: number | null
  version_number: number | null
  model: string
  judge_model: string
  case_count: number
  avg_score: number | null
  total_tokens: number
  results: EvalCaseResult[]
}

/** 历史结果记录 */
export interface EvalResultRecord extends EvalCaseResult {
  id: number
  suite_id: number
  prompt_version_id: number | null
  version_number: number | null
  model: string | null
  created_at: string | null
}

export const evalApi = {
  /** 评测集列表，可按提示词过滤 */
  suites(promptId?: number): Promise<{ items: EvalSuite[] }> {
    return http.get('/ai/eval/suites', { params: { prompt_id: promptId } })
  },

  createSuite(data: EvalSuiteCreate): Promise<EvalSuite> {
    return http.post('/ai/eval/suites', data)
  },

  deleteSuite(suiteId: number): Promise<void> {
    return http.delete(`/ai/eval/suites/${suiteId}`)
  },

  /** 执行评测（同步接口，逐用例生成并打分） */
  run(suiteId: number, data: EvalRunRequest = {}): Promise<EvalRunResult> {
    // 每道题要生成一次、评审一次，整轮常需几十秒，必须用长任务超时
    return http.post(`/ai/eval/suites/${suiteId}/run`, data, { timeout: LONG_TASK_TIMEOUT })
  },

  /** 历史结果，时间倒序 */
  results(suiteId: number, limit = 50): Promise<{ items: EvalResultRecord[] }> {
    return http.get(`/ai/eval/suites/${suiteId}/results`, { params: { limit } })
  },
}

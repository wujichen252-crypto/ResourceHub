import http, { LONG_TASK_TIMEOUT } from './http'

/** AI 能力层状态 */
export interface AIStatus {
  configured: boolean
  chat_model: string
  embedding_model: string
  embedding_dim: number
  note_count: number
  chunk_count: number
  indexed_note_count: number
  active_profile: AgentProfileSummary
  unread_proactive_count: number
}

/** 状态接口里的人格摘要 */
export interface AgentProfileSummary {
  name: string
  persona: string
  tone: string
  greeting: string | null
}

/** 智能体人格 */
export interface AgentProfile {
  id: number
  name: string
  persona: string
  tone: string
  expertise: string | null
  boundaries: string | null
  greeting: string | null
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface AgentProfilePayload {
  name: string
  persona: string
  tone: string
  expertise?: string | null
  boundaries?: string | null
  greeting?: string | null
  is_default?: boolean
}

export type AgentMemoryType = 'fact' | 'preference' | 'goal' | 'event'

/** 长期记忆 */
export interface AgentMemory {
  id: number
  profile_id: number | null
  memory_type: AgentMemoryType | string
  content: string
  importance: number
  source: string
  use_count: number
  last_used_at: string | null
  expires_at: string | null
  created_at: string
  updated_at: string
}

export interface AgentMemoryPayload {
  content: string
  memory_type?: AgentMemoryType
  importance?: number
  expires_at?: string | null
}

/** 主动消息 */
export interface AgentProactiveMessage {
  id: number
  kind: string
  title: string
  content: string
  status: 'unread' | 'read' | 'dismissed' | string
  source_ref: string | null
  created_at: string
}

export interface MemoryExtractResult {
  extracted: number
  skipped_duplicates: number
  total: number
}

export interface ProactiveScanResult {
  created: number
  skipped: number
}

/** 索引重建结果 */
export interface IndexRebuildResult {
  indexed_notes: number
  indexed_chunks: number
  skipped_notes: number
  embedding_ok: boolean
  message: string
}

/** 检索引用片段 */
export interface Citation {
  index: number
  chunk_id: number
  note_id: number
  note_title: string
  snippet: string
  score: number
}

/** Agent 单步工具调用轨迹 */
export interface AgentStep {
  step: number
  id?: string
  name: string
  arguments: string
  result?: string
}

/** 模型用量 */
export interface AIUsage {
  prompt_tokens?: number
  completion_tokens?: number
  total_tokens?: number
}

/** Agent 挂起待确认的写操作 */
export interface AwaitingConfirmation {
  run_id: number
  tool: string
  arguments: string
  message: string
}

/** 会话摘要 */
export interface ConversationSummary {
  id: number
  title: string
  model: string | null
  message_count: number
  created_at: string
  updated_at: string
}

/** 历史会话消息（citations 为后端落库的 JSON 文本） */
export interface ConversationMessage {
  id: number
  role: 'user' | 'assistant' | 'system'
  content: string
  citations: string | null
  created_at: string
}

/** RAG 问答请求体 */
export interface ChatPayload {
  message: string
  conversation_id?: number | null
  model?: string
  use_rag?: boolean
  top_k?: number
  temperature?: number
  history?: Array<{ role: 'user' | 'assistant' | 'system'; content: string }>
}

/** Agent 运行请求体 */
export interface AgentRunPayload {
  goal: string
  conversation_id?: number | null
  model?: string
  confirm_write?: boolean
  max_steps?: number
}

/** Agent 确认/拒绝请求体 */
export interface AgentResumePayload {
  run_id: number
  approve: boolean
}

/**
 * SSE 流式接口地址。
 * 流式请求走原生 fetch（axios 无法逐块读取响应体），因此这里存完整路径，不带 /api 前缀的 axios 实例。
 */
export const AI_STREAM_PATHS = {
  chat: '/api/ai/chat',
  agentRun: '/api/ai/agent/run',
  agentResume: '/api/ai/agent/resume',
} as const

export const aiApi = {
  /** 获取 AI 能力层状态与索引概况 */
  status(): Promise<AIStatus> {
    return http.get('/ai/status')
  },

  /** 重建笔记索引（不传 noteIds 则重建当前用户全部笔记） */
  rebuildIndex(noteIds?: number[]): Promise<IndexRebuildResult> {
    // 逐篇分块 + 分批向量化，耗时可达数十秒，不能沿用默认的 10 秒超时
    return http.post(
      '/ai/index/rebuild',
      { note_ids: noteIds ?? null },
      { timeout: LONG_TASK_TIMEOUT },
    )
  },

  /** 最近会话列表 */
  conversations(limit = 20): Promise<{ items: ConversationSummary[] }> {
    return http.get('/ai/conversations', { params: { limit } })
  },

  /** 指定会话的历史消息 */
  messages(conversationId: number): Promise<{ items: ConversationMessage[] }> {
    return http.get(`/ai/conversations/${conversationId}/messages`)
  },

  /** 人格列表 */
  profiles(): Promise<{ items: AgentProfile[] }> {
    return http.get('/ai/profiles')
  },

  /** 创建人格 */
  createProfile(payload: AgentProfilePayload): Promise<AgentProfile> {
    return http.post('/ai/profiles', payload)
  },

  /** 更新人格 */
  updateProfile(id: number, payload: Partial<AgentProfilePayload>): Promise<AgentProfile> {
    return http.put(`/ai/profiles/${id}`, payload)
  },

  /** 激活人格 */
  activateProfile(id: number): Promise<AgentProfile> {
    return http.put(`/ai/profiles/${id}/activate`)
  },

  /** 删除人格 */
  deleteProfile(id: number): Promise<null> {
    return http.delete(`/ai/profiles/${id}`)
  },

  /** 记忆列表 */
  memories(params?: {
    memory_type?: string
    keyword?: string
  }): Promise<{ items: AgentMemory[]; total: number }> {
    return http.get('/ai/memories', { params })
  },

  /** 手动新增记忆 */
  createMemory(payload: AgentMemoryPayload): Promise<AgentMemory> {
    return http.post('/ai/memories', payload)
  },

  /** 更新记忆 */
  updateMemory(id: number, payload: Partial<AgentMemoryPayload>): Promise<AgentMemory> {
    return http.put(`/ai/memories/${id}`, payload)
  },

  /** 删除记忆 */
  deleteMemory(id: number): Promise<null> {
    return http.delete(`/ai/memories/${id}`)
  },

  /** 清空记忆 */
  clearMemories(): Promise<{ deleted: number }> {
    return http.delete('/ai/memories')
  },

  /** 手动触发记忆抽取 */
  extractMemories(conversationId: number): Promise<MemoryExtractResult> {
    return http.post('/ai/memories/extract', { conversation_id: conversationId })
  },

  /** 主动消息列表 */
  proactiveMessages(params?: {
    status?: string
    limit?: number
  }): Promise<{ items: AgentProactiveMessage[] }> {
    return http.get('/ai/proactive/messages', { params })
  },

  /** 标记主动消息已读或忽略 */
  markProactiveRead(
    id: number,
    status: 'read' | 'dismissed' = 'read',
  ): Promise<AgentProactiveMessage> {
    return http.put(`/ai/proactive/messages/${id}/read`, null, { params: { status } })
  },

  /** 手动触发主动扫描 */
  scanProactive(): Promise<ProactiveScanResult> {
    return http.post('/ai/proactive/scan')
  },
}

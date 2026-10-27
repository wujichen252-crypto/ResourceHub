import { computed, reactive, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { ElMessage } from 'element-plus'
import { useSSE } from '../composables/useSSE'
import type { SSEData, SSEHandlers } from '../composables/useSSE'
import { getApiErrorMessage } from '../api/http'
import {
  AI_STREAM_PATHS,
  aiApi,
  type AIStatus,
  type AgentStep,
  type AwaitingConfirmation,
  type Citation,
} from '../api/ai'

/**
 * AI 工作台会话状态。
 *
 * 之所以放在 store 而不是页面组件里：用户切换页面时组件会卸载，
 * 若流式请求的生命周期绑在组件上，正在生成的回答会被中断。
 * 放在 store 后请求在路由切换时继续跑，切回来还能看到完整结果。
 */

export type AIMode = 'chat' | 'agent'

export interface ChatBubble {
  id: number
  role: 'user' | 'assistant'
  content: string
  citations: Citation[]
  steps: AgentStep[]
  streaming: boolean
  pending: AwaitingConfirmation | null
  error: string | null
}

/**
 * 会话快照存放位置。
 * 用 sessionStorage 而不是 localStorage：只在当前标签页有效，
 * 刷新可恢复，关掉标签页或退出登录即消失，不会把上一个账号的对话留给下一个人。
 */
const STORAGE_KEY = 'resourcehub:ai-workspace'

/** 读取刷新前的会话快照；数据损坏时清掉，避免每次启动都报错 */
function readSnapshot(): {
  mode: AIMode
  messages: ChatBubble[]
  input: string
  conversationId: number | null
} | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Record<string, unknown>
    return {
      mode: parsed.mode === 'agent' ? 'agent' : 'chat',
      messages: Array.isArray(parsed.messages) ? (parsed.messages as ChatBubble[]) : [],
      input: typeof parsed.input === 'string' ? parsed.input : '',
      conversationId:
        typeof parsed.conversationId === 'number' ? parsed.conversationId : null,
    }
  } catch {
    sessionStorage.removeItem(STORAGE_KEY)
    return null
  }
}

/** 恢复气泡：刷新会中断正在生成的回答，需要把状态纠正过来并给用户一句说明 */
function restoreBubbles(saved: ChatBubble[]): ChatBubble[] {
  return saved
    .filter((item) => item && typeof item === 'object')
    .map((item) => {
      const wasStreaming = item.streaming === true
      return {
        id: typeof item.id === 'number' ? item.id : 0,
        role: item.role === 'user' ? ('user' as const) : ('assistant' as const),
        content: typeof item.content === 'string' ? item.content : '',
        citations: Array.isArray(item.citations) ? item.citations : [],
        steps: Array.isArray(item.steps) ? item.steps : [],
        streaming: false,
        pending: item.pending ?? null,
        error: wasStreaming ? '页面刷新让这次回答中断了，可以重新发送。' : (item.error ?? null),
      }
    })
}

export const useAIWorkspaceStore = defineStore('aiWorkspace', () => {
  const snapshot = readSnapshot()
  const mode = ref<AIMode>(snapshot?.mode ?? 'chat')
  const messages = ref<ChatBubble[]>(restoreBubbles(snapshot?.messages ?? []))
  const input = ref(snapshot?.input ?? '')
  const conversationId = ref<number | null>(snapshot?.conversationId ?? null)
  const rebuilding = ref(false)

  const status = ref<AIStatus | null>(null)
  const statusLoading = ref(false)
  const statusError = ref<string | null>(null)

  const { isStreaming, start, abort } = useSSE()

  // 恢复的气泡已有 id，新气泡从最大值之后继续，避免 key 冲突
  let bubbleSeed = messages.value.reduce((max, item) => Math.max(max, item.id), 0)

  function nextBubbleId(): number {
    bubbleSeed += 1
    return bubbleSeed
  }

  /** 写入会话快照；隐私模式或空间不足时放弃，不影响当前会话 */
  function persist(): void {
    try {
      sessionStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          mode: mode.value,
          messages: messages.value,
          input: input.value,
          conversationId: conversationId.value,
        }),
      )
    } catch {
      /* 忽略持久化失败：会话仍可正常使用，只是刷新后无法恢复 */
    }
  }

  // 流式回答每收到一段文本都会改动 messages，合并成 500ms 一次写入，避免频繁序列化
  let persistTimer: number | undefined
  function schedulePersist(): void {
    if (persistTimer !== undefined) window.clearTimeout(persistTimer)
    persistTimer = window.setTimeout(persist, 500)
  }

  watch([mode, messages, input, conversationId], schedulePersist, { deep: true })

  // 关闭或刷新标签页前补一次写入，避免最后 500ms 的内容丢失
  window.addEventListener('pagehide', persist)

  /** 未配置模型密钥时禁止发送（后端会返回 7001） */
  const blocked = computed(() => status.value !== null && !status.value.configured)

  const statusText = computed(() => {
    if (statusLoading.value) return '检测中'
    if (statusError.value) return '状态未知'
    if (!status.value) return '状态未知'
    return status.value.configured ? 'AI 服务已就绪' : '还没填写 AI 密钥'
  })

  const indexLabel = computed(() => {
    if (!status.value) return ''
    const { indexed_note_count: indexed, note_count: total, chunk_count: chunks } = status.value
    return `AI 已读取 ${indexed}/${total} 篇笔记 · ${chunks} 个段落`
  })

  async function loadStatus(): Promise<void> {
    statusLoading.value = true
    statusError.value = null
    try {
      status.value = await aiApi.status()
    } catch (err) {
      statusError.value = getApiErrorMessage(err, '无法连接 AI 服务')
    } finally {
      statusLoading.value = false
    }
  }

  /** 手动让 AI 重新读取全部笔记 */
  async function rebuildIndex(): Promise<void> {
    if (rebuilding.value) return
    rebuilding.value = true
    try {
      const result = await aiApi.rebuildIndex()
      ElMessage.success(result.message || `AI 已读取 ${result.indexed_notes} 篇笔记`)
      await loadStatus()
    } catch {
      // http 拦截器已提示具体错误
    } finally {
      rebuilding.value = false
    }
  }

  // 切换模式后旧会话上下文不再适用，重新开一条会话
  watch(mode, () => {
    conversationId.value = null
  })

  /** SSE 引用事件 → 强类型引用对象 */
  function toCitation(data: SSEData): Citation {
    return {
      index: typeof data.index === 'number' ? data.index : 0,
      chunk_id: typeof data.chunk_id === 'number' ? data.chunk_id : 0,
      note_id: typeof data.note_id === 'number' ? data.note_id : 0,
      note_title: typeof data.note_title === 'string' ? data.note_title : '未命名笔记',
      snippet: typeof data.snippet === 'string' ? data.snippet : '',
      score: typeof data.score === 'number' ? data.score : 0,
    }
  }

  /** 问答模式事件处理 */
  function buildChatHandlers(bubble: ChatBubble): SSEHandlers {
    return {
      onMeta(data) {
        if (typeof data.conversation_id === 'number') conversationId.value = data.conversation_id
      },
      onToken(data) {
        if (typeof data.text === 'string') bubble.content += data.text
      },
      onCitation(data) {
        bubble.citations.push(toCitation(data))
      },
      onDone() {
        bubble.streaming = false
      },
      onError(data) {
        bubble.streaming = false
        bubble.error = typeof data.message === 'string' ? data.message : 'AI 服务出了问题，请稍后再试'
      },
    }
  }

  /** Agent 模式事件处理（含操作过程与写操作确认） */
  function buildAgentHandlers(bubble: ChatBubble): SSEHandlers {
    return {
      onToken(data) {
        if (typeof data.text === 'string') bubble.content += data.text
      },
      onToolCall(data) {
        bubble.steps.push({
          step: typeof data.step === 'number' ? data.step : bubble.steps.length + 1,
          id: typeof data.id === 'string' ? data.id : undefined,
          name: typeof data.name === 'string' ? data.name : '未知操作',
          arguments: typeof data.arguments === 'string' ? data.arguments : '{}',
        })
      },
      onToolResult(data) {
        const name = typeof data.name === 'string' ? data.name : ''
        const result = typeof data.result === 'string' ? data.result : ''
        // 回填到最近一个同名且尚无结果的步骤；确认恢复时没有对应的 tool_call，直接追加一条
        for (let i = bubble.steps.length - 1; i >= 0; i -= 1) {
          const step = bubble.steps[i]
          if (step.name === name && step.result === undefined) {
            step.result = result
            return
          }
        }
        bubble.steps.push({
          step: bubble.steps.length + 1,
          name: name || '未知操作',
          arguments: '',
          result,
        })
      },
      onAwaitingConfirmation(data) {
        bubble.pending = {
          run_id: typeof data.run_id === 'number' ? data.run_id : 0,
          tool: typeof data.tool === 'string' ? data.tool : '未知操作',
          arguments: typeof data.arguments === 'string' ? data.arguments : '{}',
          message: typeof data.message === 'string' ? data.message : '该操作需要确认',
        }
        bubble.streaming = false
      },
      onDone(data) {
        bubble.streaming = false
        if (data.cancelled === true && !bubble.content) {
          bubble.content = '已取消这次修改，笔记没有任何变化。'
        }
      },
      onError(data) {
        bubble.streaming = false
        bubble.error = typeof data.message === 'string' ? data.message : 'AI 服务出了问题，请稍后再试'
      },
    }
  }

  /** 发送当前输入：按模式分流到问答或自动助手 */
  async function send(): Promise<void> {
    const text = input.value.trim()
    if (!text || isStreaming.value) return
    if (blocked.value) {
      ElMessage.warning('AI 服务还没启用，暂时不能用')
      return
    }

    input.value = ''

    const userBubble = reactive<ChatBubble>({
      id: nextBubbleId(),
      role: 'user',
      content: text,
      citations: [],
      steps: [],
      streaming: false,
      pending: null,
      error: null,
    })
    const assistantBubble = reactive<ChatBubble>({
      id: nextBubbleId(),
      role: 'assistant',
      content: '',
      citations: [],
      steps: [],
      streaming: true,
      pending: null,
      error: null,
    })
    messages.value.push(userBubble, assistantBubble)

    if (mode.value === 'chat') {
      // 只带对话历史，当前两条消息已经在服务端本次请求里
      const history = messages.value
        .slice(0, messages.value.length - 2)
        .filter((item) => item.role === 'user' || item.role === 'assistant')
        .map((item) => ({ role: item.role, content: item.content }))
        .slice(-20)

      await start(AI_STREAM_PATHS.chat, buildChatHandlers(assistantBubble), {
        body: {
          message: text,
          conversation_id: conversationId.value,
          use_rag: true,
          top_k: 4,
          history,
        },
      })
    } else {
      await start(AI_STREAM_PATHS.agentRun, buildAgentHandlers(assistantBubble), {
        body: { goal: text, max_steps: 6 },
      })
    }

    assistantBubble.streaming = false
    // 流异常中断且没有任何产出时补一句提示，避免出现空气泡
    if (
      !assistantBubble.content &&
      !assistantBubble.error &&
      !assistantBubble.pending &&
      !assistantBubble.steps.length
    ) {
      assistantBubble.content = '未收到响应，请重试。'
    }
  }

  /** 停止生成：保留已生成内容 */
  function stop(): void {
    abort()
    const last = messages.value[messages.value.length - 1]
    if (last && last.role === 'assistant') last.streaming = false
  }

  /** 确认或拒绝自动助手挂起的写操作 */
  async function resolvePending(bubble: ChatBubble, approve: boolean): Promise<void> {
    if (!bubble.pending || isStreaming.value) return
    const runId = bubble.pending.run_id
    bubble.pending = null
    if (!runId) {
      bubble.error = '这次操作已失效，请重新发起'
      return
    }
    bubble.streaming = true

    await start(AI_STREAM_PATHS.agentResume, buildAgentHandlers(bubble), {
      body: { run_id: runId, approve },
    })
    bubble.streaming = false
  }

  function newConversation(): void {
    if (isStreaming.value) abort()
    messages.value = []
    conversationId.value = null
    input.value = ''
  }

  /** 退出登录时清空，避免下一个账号看到上一个账号的对话 */
  function reset(): void {
    abort()
    if (persistTimer !== undefined) window.clearTimeout(persistTimer)
    messages.value = []
    conversationId.value = null
    input.value = ''
    mode.value = 'chat'
    status.value = null
    try {
      sessionStorage.removeItem(STORAGE_KEY)
    } catch {
      /* 忽略清理失败 */
    }
  }

  return {
    mode,
    messages,
    input,
    conversationId,
    rebuilding,
    status,
    statusLoading,
    statusError,
    isStreaming,
    blocked,
    statusText,
    indexLabel,
    loadStatus,
    rebuildIndex,
    send,
    stop,
    resolvePending,
    newConversation,
    reset,
  }
})

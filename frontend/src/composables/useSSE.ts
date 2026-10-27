import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'

/**
 * SSE 流式请求组合式函数。
 *
 * 后端事件协议（每个事件为 `event: xxx\ndata: {json}\n\n`）：
 * meta / token / citation / tool_call / tool_result / awaiting_confirmation / done / error
 *
 * 使用 fetch + ReadableStream 而非 EventSource：
 * EventSource 只支持 GET 且无法携带 Authorization 头，而这里需要 POST + JWT。
 */

/** 事件数据：后端均为扁平 JSON 对象，具体字段由调用方按事件语义收窄 */
export type SSEData = Record<string, unknown>
export type SSEHandler = (data: SSEData) => void

export interface SSEHandlers {
  /** 任意事件都会先触发，便于统一留痕 */
  onEvent?: (event: string, data: SSEData) => void
  onMeta?: SSEHandler
  onToken?: SSEHandler
  onCitation?: SSEHandler
  onToolCall?: SSEHandler
  onToolResult?: SSEHandler
  onAwaitingConfirmation?: SSEHandler
  onDone?: SSEHandler
  onError?: SSEHandler
}

export interface SSEOptions {
  /** POST 请求体，内部会 JSON.stringify */
  body?: unknown
  /** 额外请求头 */
  headers?: Record<string, string>
}

/** 解析单个 SSE 帧；注释帧与无数据帧返回 null */
function parseFrame(raw: string): { event: string; data: SSEData } | null {
  let event = 'message'
  const dataLines: string[] = []

  for (const line of raw.split('\n')) {
    if (!line || line.startsWith(':')) continue
    if (line.startsWith('event:')) {
      event = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).replace(/^ /, ''))
    }
  }

  if (dataLines.length === 0) return null

  const payload = dataLines.join('\n')
  try {
    const parsed: unknown = JSON.parse(payload)
    // 后端保证 data 为对象；万一为 null 或标量则包一层，避免调用方判空
    if (parsed && typeof parsed === 'object') {
      return { event, data: parsed as SSEData }
    }
    return { event, data: { value: parsed } }
  } catch {
    // 非 JSON 数据（如纯文本心跳）按 text 字段透传
    return { event, data: { text: payload } }
  }
}

/** 从非流式错误响应里提取可读文案（后端 APIError 返回 {code, msg}） */
async function readErrorBody(response: Response): Promise<string> {
  try {
    const text = await response.text()
    if (!text) return ''
    const parsed: unknown = JSON.parse(text)
    if (parsed && typeof parsed === 'object') {
      const record = parsed as Record<string, unknown>
      const message = record.msg ?? record.detail ?? record.message
      if (typeof message === 'string') return message
    }
    return text.slice(0, 200)
  } catch {
    return ''
  }
}

/** 按事件名分发到对应回调 */
function dispatch(event: string, data: SSEData, handlers: SSEHandlers): void {
  const table: Record<string, SSEHandler | undefined> = {
    meta: handlers.onMeta,
    token: handlers.onToken,
    citation: handlers.onCitation,
    tool_call: handlers.onToolCall,
    tool_result: handlers.onToolResult,
    awaiting_confirmation: handlers.onAwaitingConfirmation,
    done: handlers.onDone,
    error: handlers.onError,
  }
  table[event]?.(data)
  handlers.onEvent?.(event, data)
}

/** 把 fetch 层异常翻译成中文，避免把 "network error" / "Failed to fetch" 原文抛给用户 */
function describeStreamError(err: unknown): string {
  const raw = err instanceof Error ? err.message : ''
  if (err instanceof TypeError || /network|failed to fetch|load failed/i.test(raw)) {
    return '网络中断了，请检查网络后重试'
  }
  return raw || '请求失败，请稍后重试'
}

export function useSSE() {
  const isStreaming = ref(false)
  const error = ref<string | null>(null)
  let controller: AbortController | null = null

  /** 中断当前流；由持有方在需要时调用（例如用户点「停止」或切换会话） */
  function abort(): void {
    controller?.abort()
    controller = null
    isStreaming.value = false
  }

  /** 发起一次 SSE 请求，返回的 Promise 在流结束（或失败/中断）后 resolve */
  async function start(url: string, handlers: SSEHandlers, options: SSEOptions = {}): Promise<void> {
    abort()
    controller = new AbortController()
    const current = controller
    isStreaming.value = true
    error.value = null

    const authStore = useAuthStore()

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
          ...(authStore.accessToken ? { Authorization: `Bearer ${authStore.accessToken}` } : {}),
          ...options.headers,
        },
        body: JSON.stringify(options.body ?? {}),
        signal: current.signal,
      })

      const contentType = response.headers.get('content-type') || ''
      // 未配置密钥等前置校验失败时，后端返回 JSON 错误而非事件流
      if (!response.ok || !contentType.includes('text/event-stream')) {
        const detail = await readErrorBody(response)
        throw new Error(detail || `请求失败（HTTP ${response.status}）`)
      }
      if (!response.body) {
        throw new Error('当前浏览器不支持流式响应')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''

      while (true) {
        const { value, done } = await reader.read()
        if (done) break

        // 统一换行符，避免代理层返回 \r\n 导致帧切分失败
        buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n')

        let boundary = buffer.indexOf('\n\n')
        while (boundary !== -1) {
          const frame = buffer.slice(0, boundary)
          buffer = buffer.slice(boundary + 2)
          const parsed = parseFrame(frame)
          if (parsed) {
            if (parsed.event === 'error') {
              const message = parsed.data.message
              error.value = typeof message === 'string' ? message : 'AI 服务异常'
            }
            dispatch(parsed.event, parsed.data, handlers)
          }
          boundary = buffer.indexOf('\n\n')
        }
      }

      // 末尾未以空行结束的残留帧
      const tail = parseFrame(buffer)
      if (tail) {
        if (tail.event === 'error') {
          const message = tail.data.message
          error.value = typeof message === 'string' ? message : 'AI 服务异常'
        }
        dispatch(tail.event, tail.data, handlers)
      }
    } catch (err) {
      // 用户主动中断不算异常
      if (err instanceof Error && err.name === 'AbortError') return
      const message = describeStreamError(err)
      error.value = message
      handlers.onError?.({ message })
    } finally {
      if (controller === current) {
        controller = null
        isStreaming.value = false
      }
    }
  }

  // 注意：这里不注册 onUnmounted。流式请求的生命周期由调用方（AI 工作台的 store）管理，
  // 否则用户切换路由导致组件卸载时，正在生成的回答会被强行中断。

  return { isStreaming, error, start, abort }
}

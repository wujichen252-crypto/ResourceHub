import axios from 'axios'
import type { AxiosError, AxiosInstance, InternalAxiosRequestConfig, AxiosResponse } from 'axios'
import { useAuthStore } from '../stores/auth'
import { ElMessage } from 'element-plus'

/**
 * 长任务超时（毫秒）。
 * 索引重建、提示词评测需要多次调用模型，普通请求的 10 秒必然不够；
 * 这类接口必须显式传入该超时，否则用户会看到“请求超时”而后台其实还在执行。
 */
export const LONG_TASK_TIMEOUT = 300000

/** 把网络层异常翻译成用户能看懂的中文，避免直接暴露 Network Error / timeout 英文原文 */
function describeNetworkError(error: AxiosError): string {
  if (error.code === 'ECONNABORTED' || /timeout/i.test(error.message)) {
    return '等待时间过长，服务没有响应，请稍后再试'
  }
  if (!error.response) {
    return '网络连接不可用，请检查网络后重试'
  }
  const status = error.response.status
  if (status === 403) return '没有权限执行这个操作'
  if (status === 429) return '操作太频繁，请稍后再试'
  if (status >= 500) return '服务暂时不可用，请稍后再试'
  return '请求失败，请稍后再试'
}

export interface ApiResponse<T = any> {
  code: number
  data: T
  msg: string
}

const http: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

http.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const authStore = useAuthStore()
    if (authStore.accessToken) {
      config.headers.Authorization = `Bearer ${authStore.accessToken}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

http.interceptors.response.use(
  (response: AxiosResponse) => {
    const res = response.data
    // 如果响应中有 code 字段且不为 200/201，视为业务错误
    if (res?.code !== undefined && res.code !== 200 && res.code !== 201) {
      ElMessage.error(res.msg || '请求失败')
      return Promise.reject(new Error(res.msg || '请求失败'))
    }
    // 有 data 字段 → 返回 data；没有 → 直接返回整个响应体
    return (res?.data !== undefined ? res.data : res) as any
  },
  async (error) => {
    const originalRequest = error.config
    const authStore = useAuthStore()

    // 刷新请求自身 401 → 会话已失效，直接登出并跳转登录页（避免无限刷新循环）
    if (error.response?.status === 401 && originalRequest?.url?.includes('/auth/refresh')) {
      authStore.logout()
      redirectToLogin()
      return Promise.reject(error)
    }

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      if (!authStore.refreshToken) {
        authStore.logout()
        redirectToLogin()
        return Promise.reject(error)
      }

      try {
        await authStore.refreshTokenAction()
        originalRequest.headers.Authorization = `Bearer ${authStore.accessToken}`
        return http(originalRequest)
      } catch {
        authStore.logout()
        redirectToLogin()
        return Promise.reject(error)
      }
    }

    if (error.response?.data?.msg) {
      ElMessage.error(error.response.data.msg)
    } else {
      ElMessage.error(describeNetworkError(error))
    }

    return Promise.reject(error)
  },
)

/** 从请求异常中提取可展示的文案：优先取后端 msg，其次取 Error.message */
export function getApiErrorMessage(error: unknown, fallback = '请求失败'): string {
  if (axios.isAxiosError(error)) {
    const payload = error.response?.data as { msg?: string } | undefined
    if (payload?.msg) return payload.msg
    return describeNetworkError(error)
  }
  return error instanceof Error ? error.message : fallback
}

/** 会话失效后跳转到登录页，保留当前路径以便登录后返回 */
function redirectToLogin() {
  if (window.location.pathname.startsWith('/login')) return
  const redirect = encodeURIComponent(window.location.pathname + window.location.search)
  window.location.href = `/login?redirect=${redirect}`
}

export default http

import axios from 'axios'
import type { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse } from 'axios'
import { useAuthStore } from '../stores/auth'
import { ElMessage } from 'element-plus'

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
    } else if (error.message) {
      ElMessage.error(error.message)
    }

    return Promise.reject(error)
  },
)

/** 会话失效后跳转到登录页，保留当前路径以便登录后返回 */
function redirectToLogin() {
  if (window.location.pathname.startsWith('/login')) return
  const redirect = encodeURIComponent(window.location.pathname + window.location.search)
  window.location.href = `/login?redirect=${redirect}`
}

export default http

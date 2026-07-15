import axios from 'axios'
import type { AxiosInstance, InternalAxiosRequestConfig } from 'axios'
import { useAuthStore } from '../stores/auth'

const http: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器 — 自动附加 Authorization Header
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

// 响应拦截器 — 401 自动尝试刷新 Token
http.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      const authStore = useAuthStore()
      try {
        await authStore.refreshToken()
        // 刷新成功，使用新 Token 重试原请求
        originalRequest.headers.Authorization = `Bearer ${authStore.accessToken}`
        return http(originalRequest)
      } catch {
        // 刷新失败，跳转到登录页
        authStore.logout()
        return Promise.reject(error)
      }
    }

    return Promise.reject(error)
  },
)

export default http

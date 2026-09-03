import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '../api/auth'
import type { User, LoginRequest, RegisterRequest } from '../api/auth'

export interface JwtPayload {
  sub?: string
  exp?: number
  type?: string
  [key: string]: unknown
}

/** 解析 JWT payload，解析失败返回 null */
export function parseJwtPayload(token: string): JwtPayload | null {
  try {
    const base64Url = token.split('.')[1]
    if (!base64Url) return null
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const json = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join(''),
    )
    return JSON.parse(json) as JwtPayload
  } catch {
    return null
  }
}

/** 判断 JWT 是否已过期（无法解析按过期处理） */
export function isTokenExpired(token: string): boolean {
  const payload = parseJwtPayload(token)
  if (!payload || typeof payload.exp !== 'number') return true
  return payload.exp * 1000 <= Date.now()
}

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref<User | null>(null)
  const accessToken = ref<string | null>(localStorage.getItem('accessToken'))
  const refreshToken = ref<string | null>(localStorage.getItem('refreshToken'))

  // Getters
  const isAuthenticated = computed(() => !!accessToken.value)

  // Actions
  async function login(data: LoginRequest) {
    const response = await authApi.login(data)
    accessToken.value = response.access_token
    refreshToken.value = response.refresh_token

    localStorage.setItem('accessToken', response.access_token)
    localStorage.setItem('refreshToken', response.refresh_token)

    await fetchUser()
  }

  async function register(data: RegisterRequest) {
    await authApi.register(data)
    await login({ username: data.username, password: data.password })
  }

  async function fetchUser() {
    user.value = await authApi.me()
  }

  async function refreshTokenAction() {
    if (!refreshToken.value) throw new Error('No refresh token')

    const response = await authApi.refresh(refreshToken.value)
    accessToken.value = response.access_token
    refreshToken.value = response.refresh_token

    localStorage.setItem('accessToken', response.access_token)
    localStorage.setItem('refreshToken', response.refresh_token)
  }

  function logout() {
    user.value = null
    accessToken.value = null
    refreshToken.value = null

    localStorage.removeItem('accessToken')
    localStorage.removeItem('refreshToken')
  }

  return {
    user,
    accessToken,
    refreshToken,
    isAuthenticated,
    login,
    register,
    fetchUser,
    refreshTokenAction,
    logout,
  }
})

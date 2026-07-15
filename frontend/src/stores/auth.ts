import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '../api/auth'
import type { User, LoginRequest, RegisterRequest } from '../api/auth'

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
    refreshToken: refreshTokenAction,
    logout,
  }
})

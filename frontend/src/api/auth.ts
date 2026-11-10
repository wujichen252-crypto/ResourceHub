import http from './http'

export interface User {
  id: number
  username: string
  email: string | null
  avatar: string | null
  created_at: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  password: string
  email?: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export const authApi = {
  login(data: LoginRequest): Promise<TokenResponse> {
    return http.post('/auth/login', data)
  },

  register(data: RegisterRequest): Promise<User> {
    return http.post('/auth/register', data)
  },

  refresh(refreshToken: string): Promise<TokenResponse> {
    return http.post('/auth/refresh', { refresh_token: refreshToken })
  },

  me(): Promise<User> {
    return http.get('/auth/me')
  },

  requestPasswordResetCode(data: { username: string; email: string }): Promise<void> {
    return http.post('/auth/password-reset/request', data)
  },

  confirmPasswordReset(data: {
    username: string
    email: string
    code: string
    new_password: string
  }): Promise<void> {
    return http.post('/auth/password-reset/confirm', data)
  },

  changePassword(data: { old_password: string; new_password: string }): Promise<void> {
    return http.put('/auth/change-password', data)
  },
}

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
    return http.post('/auth/login', data).then((res) => res.data.data)
  },

  register(data: RegisterRequest): Promise<User> {
    return http.post('/auth/register', data).then((res) => res.data.data)
  },

  refresh(refreshToken: string): Promise<TokenResponse> {
    return http.post('/auth/refresh', { refresh_token: refreshToken }).then((res) => res.data.data)
  },

  me(): Promise<User> {
    return http.get('/auth/me').then((res) => res.data.data)
  },
}

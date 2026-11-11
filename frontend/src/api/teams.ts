import http from './http'

/** 团队角色：创建者 / 管理员 / 普通成员 */
export type TeamRole = 'owner' | 'admin' | 'member'

export interface Team {
  id: number
  name: string
  description: string | null
  owner_id: number
  invite_code: string
  /** 当前登录用户在团队中的角色 */
  role: TeamRole
  member_count: number
  note_count: number
  prompt_count: number
  created_at: string
  updated_at: string
}

export interface TeamMember {
  id: number
  user_id: number
  username: string
  avatar: string | null
  role: TeamRole
  joined_at: string
}

export const teamsApi = {
  list(): Promise<Team[]> {
    return http.get('/teams')
  },

  create(data: { name: string; description?: string }): Promise<Team> {
    return http.post('/teams', data)
  },

  get(id: number): Promise<Team> {
    return http.get(`/teams/${id}`)
  },

  update(id: number, data: { name?: string; description?: string }): Promise<Team> {
    return http.put(`/teams/${id}`, data)
  },

  remove(id: number): Promise<void> {
    return http.delete(`/teams/${id}`)
  },

  join(inviteCode: string): Promise<Team> {
    return http.post('/teams/join', { invite_code: inviteCode })
  },

  regenerateInvite(id: number): Promise<{ invite_code: string }> {
    return http.post(`/teams/${id}/invite/regenerate`)
  },

  leave(id: number): Promise<void> {
    return http.post(`/teams/${id}/leave`)
  },

  members(id: number): Promise<TeamMember[]> {
    return http.get(`/teams/${id}/members`)
  },

  updateMemberRole(id: number, userId: number, role: 'admin' | 'member'): Promise<TeamMember> {
    return http.put(`/teams/${id}/members/${userId}`, { role })
  },

  removeMember(id: number, userId: number): Promise<void> {
    return http.delete(`/teams/${id}/members/${userId}`)
  },
}

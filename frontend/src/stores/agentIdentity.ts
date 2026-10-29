import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import {
  aiApi,
  type AgentMemory,
  type AgentMemoryPayload,
  type AgentProfile,
  type AgentProfilePayload,
  type AgentProactiveMessage,
  type AIStatus,
  type ProactiveScanResult,
} from '../api/ai'
import { getApiErrorMessage } from '../api/http'

/**
 * 智能体身份层状态：人格、长期记忆与主动消息。
 *
 * 与 aiWorkspace 分开：后者只负责对话与流式请求，这里负责「它是谁、记得什么、主动说了什么」。
 */
export const useAgentIdentityStore = defineStore('agentIdentity', () => {
  const status = ref<AIStatus | null>(null)
  const profiles = ref<AgentProfile[]>([])
  const memories = ref<AgentMemory[]>([])
  const proactive = ref<AgentProactiveMessage[]>([])
  const unreadCount = ref(0)
  const loading = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)

  const activeProfile = computed(
    () => profiles.value.find((item) => item.is_default) ?? null,
  )
  const profileName = computed(
    () => activeProfile.value?.name || status.value?.active_profile?.name || 'AI 助手',
  )
  const personaTagline = computed(
    () =>
      activeProfile.value?.persona ||
      status.value?.active_profile?.persona ||
      '你的个人知识搭档',
  )
  const greeting = computed(
    () =>
      activeProfile.value?.greeting ||
      status.value?.active_profile?.greeting ||
      '我是你的知识搭档，问我任何你笔记里的问题。',
  )

  async function loadStatus(): Promise<void> {
    try {
      status.value = await aiApi.status()
      unreadCount.value = status.value.unread_proactive_count ?? 0
    } catch (err) {
      error.value = getApiErrorMessage(err, '无法读取智能体状态')
    }
  }

  async function loadProfiles(): Promise<void> {
    try {
      const data = await aiApi.profiles()
      profiles.value = data.items
    } catch (err) {
      error.value = getApiErrorMessage(err, '无法读取人格配置')
    }
  }

  async function loadMemories(type?: string, keyword?: string): Promise<void> {
    try {
      const data = await aiApi.memories({ memory_type: type, keyword })
      memories.value = data.items
    } catch (err) {
      error.value = getApiErrorMessage(err, '无法读取记忆')
    }
  }

  async function loadProactive(statusFilter?: string): Promise<void> {
    try {
      const data = await aiApi.proactiveMessages({
        status: statusFilter,
        limit: 30,
      })
      proactive.value = data.items
    } catch (err) {
      error.value = getApiErrorMessage(err, '无法读取主动消息')
    }
  }

  /** 打开设置抽屉时一次性加载三类数据，互不阻塞 */
  async function loadPanels(): Promise<void> {
    loading.value = true
    error.value = null
    await Promise.allSettled([
      loadStatus(),
      loadProfiles(),
      loadMemories(),
      loadProactive(),
    ])
    loading.value = false
  }

  async function saveProfile(payload: AgentProfilePayload): Promise<void> {
    saving.value = true
    try {
      if (activeProfile.value) {
        await aiApi.updateProfile(activeProfile.value.id, payload)
      } else {
        await aiApi.createProfile({ ...payload, is_default: true })
      }
      await Promise.all([loadProfiles(), loadStatus()])
    } finally {
      saving.value = false
    }
  }

  async function activateProfile(id: number): Promise<void> {
    await aiApi.activateProfile(id)
    await Promise.all([loadProfiles(), loadStatus()])
  }

  async function deleteProfile(id: number): Promise<void> {
    await aiApi.deleteProfile(id)
    await Promise.all([loadProfiles(), loadStatus()])
  }

  async function addMemory(payload: AgentMemoryPayload): Promise<void> {
    saving.value = true
    try {
      await aiApi.createMemory(payload)
      await loadMemories()
    } finally {
      saving.value = false
    }
  }

  async function updateMemory(
    id: number,
    payload: Partial<AgentMemoryPayload>,
  ): Promise<void> {
    await aiApi.updateMemory(id, payload)
    await loadMemories()
  }

  async function removeMemory(id: number): Promise<void> {
    await aiApi.deleteMemory(id)
    await loadMemories()
  }

  async function clearMemories(): Promise<void> {
    await aiApi.clearMemories()
    memories.value = []
  }

  async function markRead(
    id: number,
    next: 'read' | 'dismissed' = 'read',
  ): Promise<void> {
    const previous = proactive.value.find((item) => item.id === id)
    const wasUnread = previous?.status === 'unread'
    const updated = await aiApi.markProactiveRead(id, next)
    const index = proactive.value.findIndex((item) => item.id === id)
    if (index !== -1) proactive.value[index] = updated
    if (wasUnread) unreadCount.value = Math.max(0, unreadCount.value - 1)
  }

  async function scan(): Promise<ProactiveScanResult> {
    const result = await aiApi.scanProactive()
    await Promise.all([loadProactive(), loadStatus()])
    return result
  }

  function reset(): void {
    status.value = null
    profiles.value = []
    memories.value = []
    proactive.value = []
    unreadCount.value = 0
    error.value = null
  }

  return {
    status,
    profiles,
    memories,
    proactive,
    unreadCount,
    loading,
    saving,
    error,
    activeProfile,
    profileName,
    personaTagline,
    greeting,
    loadStatus,
    loadProfiles,
    loadMemories,
    loadProactive,
    loadPanels,
    saveProfile,
    activateProfile,
    deleteProfile,
    addMemory,
    updateMemory,
    removeMemory,
    clearMemories,
    markRead,
    scan,
    reset,
  }
})

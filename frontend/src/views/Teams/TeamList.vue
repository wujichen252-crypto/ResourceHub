<template>
  <div class="rh-page">
    <div class="page-header">
      <div class="page-heading">
        <h1 class="page-title">团队空间</h1>
        <p class="page-subtitle">把个人沉淀升级为团队知识库：共享笔记与提示词，AI 问答自动检索团队内容</p>
      </div>
      <div class="header-actions">
        <el-button @click="joinVisible = true">
          <el-icon><Connection /></el-icon>加入团队
        </el-button>
        <el-button type="primary" @click="openCreate">
          <el-icon><Plus /></el-icon>新建团队
        </el-button>
      </div>
    </div>

    <LoadingState v-if="loading" variant="card" />

    <ErrorState
      v-else-if="error"
      title="团队列表加载失败"
      description="请检查网络连接后重试"
      @retry="load"
    />

    <div v-else-if="teams.length" class="team-grid">
      <el-card
        v-for="team in teams"
        :key="team.id"
        shadow="never"
        class="team-card"
        role="link"
        tabindex="0"
        :aria-label="`进入团队「${team.name}」`"
        @click="router.push(`/teams/${team.id}`)"
        @keydown.enter.prevent="router.push(`/teams/${team.id}`)"
      >
        <div class="team-head">
          <span class="team-mark" aria-hidden="true">{{ team.name.charAt(0) }}</span>
          <div class="team-title">
            <h3>{{ team.name }}</h3>
            <span class="team-role">{{ roleLabel(team.role) }}</span>
          </div>
        </div>
        <p class="team-desc">{{ team.description || '暂无团队简介' }}</p>
        <div class="team-stats">
          <span>{{ team.member_count }} 成员</span>
          <span>{{ team.note_count }} 笔记</span>
          <span>{{ team.prompt_count }} 提示词</span>
        </div>
      </el-card>
    </div>

    <EmptyState
      v-else
      :icon="OfficeBuilding"
      title="还没有加入团队"
      description="创建一个团队，或用邀请码加入同事的知识库"
    >
      <el-button type="primary" @click="openCreate">创建第一个团队</el-button>
    </EmptyState>

    <el-dialog v-model="createVisible" title="新建团队" width="440px" :close-on-click-modal="false">
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="团队名称" required>
          <el-input v-model="createForm.name" maxlength="100" show-word-limit placeholder="例如：前端研发组" />
        </el-form-item>
        <el-form-item label="团队简介">
          <el-input
            v-model="createForm.description"
            type="textarea"
            :rows="3"
            maxlength="500"
            show-word-limit
            placeholder="这个团队沉淀什么内容？"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="joinVisible" title="加入团队" width="440px" :close-on-click-modal="false">
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="邀请码" required>
          <el-input
            v-model="joinCode"
            maxlength="16"
            placeholder="输入 8 位邀请码，例如 AB3D7K9M"
            @keyup.enter="submitJoin"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="joinVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitJoin">加入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Connection, OfficeBuilding, Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { teamsApi } from '../../api/teams'
import type { Team, TeamRole } from '../../api/teams'
import { getApiErrorMessage } from '../../api/http'
import EmptyState from '../../components/common/EmptyState.vue'
import ErrorState from '../../components/common/ErrorState.vue'
import LoadingState from '../../components/common/LoadingState.vue'

const router = useRouter()

const teams = ref<Team[]>([])
const loading = ref(true)
const error = ref(false)
const submitting = ref(false)

const createVisible = ref(false)
const createForm = reactive({ name: '', description: '' })
const joinVisible = ref(false)
const joinCode = ref('')

const ROLE_LABELS: Record<TeamRole, string> = {
  owner: '创建者',
  admin: '管理员',
  member: '成员',
}

function roleLabel(role: TeamRole): string {
  return ROLE_LABELS[role] || '成员'
}

/** 拉取我加入的团队；失败时置 error 交给 ErrorState 重试 */
async function load() {
  loading.value = true
  error.value = false
  try {
    teams.value = await teamsApi.list()
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

function openCreate() {
  createForm.name = ''
  createForm.description = ''
  createVisible.value = true
}

async function submitCreate() {
  if (!createForm.name.trim()) {
    ElMessage.warning('请填写团队名称')
    return
  }
  submitting.value = true
  try {
    const team = await teamsApi.create({
      name: createForm.name.trim(),
      description: createForm.description.trim() || undefined,
    })
    createVisible.value = false
    ElMessage.success('团队创建成功')
    router.push(`/teams/${team.id}`)
  } catch (err) {
    ElMessage.error(getApiErrorMessage(err, '创建团队失败'))
  } finally {
    submitting.value = false
  }
}

async function submitJoin() {
  const code = joinCode.value.trim()
  if (!code) {
    ElMessage.warning('请输入邀请码')
    return
  }
  submitting.value = true
  try {
    const team = await teamsApi.join(code)
    joinVisible.value = false
    joinCode.value = ''
    ElMessage.success(`已加入「${team.name}」`)
    router.push(`/teams/${team.id}`)
  } catch (err) {
    ElMessage.error(getApiErrorMessage(err, '加入团队失败'))
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 24px; }
.page-heading { min-width: 0; }
.page-title { margin: 0; font-size: 26px; font-weight: 700; color: var(--rh-text-primary); }
.page-subtitle { margin: 8px 0 0; max-width: 640px; color: var(--rh-text-secondary); font-size: 13px; line-height: 1.7; }
.header-actions { display: flex; gap: 8px; }

.team-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.team-card { cursor: pointer; border: 1px solid var(--rh-border-faint); transition: border-color .18s ease, box-shadow .18s ease, transform .18s ease; }
.team-card:hover, .team-card:focus-visible { border-color: var(--rh-border-strong); box-shadow: var(--rh-shadow-md); transform: translateY(-2px); }
.team-card :deep(.el-card__body) { display: flex; flex-direction: column; gap: 12px; padding: 20px; }
.team-head { display: flex; align-items: center; gap: 12px; }
.team-mark { display: grid; place-items: center; width: 40px; height: 40px; border-radius: var(--rh-radius-md); background: var(--rh-bg-active); color: var(--rh-primary); font-family: Georgia, serif; font-size: 20px; font-weight: 700; }
.team-title { min-width: 0; }
.team-title h3 { margin: 0; font-size: 16px; font-weight: 600; color: var(--rh-text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.team-role { display: inline-block; margin-top: 4px; color: var(--rh-text-tertiary); font-size: 12px; }
.team-desc { margin: 0; min-height: 40px; color: var(--rh-text-secondary); font-size: 13px; line-height: 1.6; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.team-stats { display: flex; gap: 14px; padding-top: 12px; border-top: 1px solid var(--rh-border-faint); color: var(--rh-text-tertiary); font-size: 12px; }

@media (max-width: 640px) {
  .page-title { font-size: 22px; }
  .header-actions { width: 100%; }
  .header-actions :deep(.el-button) { flex: 1; }
}
</style>

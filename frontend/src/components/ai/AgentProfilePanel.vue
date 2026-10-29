<template>
  <div class="identity-panel">
    <LoadingState
      v-if="identity.loading"
      variant="row"
      :count="3"
      label="正在读取人格"
    />
    <ErrorState
      v-else-if="identity.error"
      title="人格加载失败"
      :description="identity.error"
      @retry="reload"
    />
    <form v-else class="profile-form" @submit.prevent="save">
      <div class="field">
        <label for="agent-name">名字</label>
        <el-input
          id="agent-name"
          v-model="form.name"
          maxlength="50"
          show-word-limit
          placeholder="例如：阿枢"
        />
      </div>

      <div class="field">
        <label for="agent-persona">角色定位</label>
        <el-input
          id="agent-persona"
          v-model="form.persona"
          type="textarea"
          :rows="3"
          maxlength="2000"
          show-word-limit
          placeholder="例如：你的前端学习搭档，帮你把零散知识串成学习路径"
        />
      </div>

      <div class="field">
        <span class="field-label">语气风格</span>
        <el-radio-group v-model="form.tone">
          <el-radio-button value="严谨">严谨</el-radio-button>
          <el-radio-button value="轻松">轻松</el-radio-button>
          <el-radio-button value="激励">激励</el-radio-button>
        </el-radio-group>
      </div>

      <div class="field">
        <label for="agent-expertise">专业领域</label>
        <el-input
          id="agent-expertise"
          v-model="form.expertise"
          maxlength="200"
          placeholder="例如：Vue 3 / TypeScript / 前端工程化"
        />
      </div>

      <div class="field">
        <label for="agent-boundaries">边界</label>
        <el-input
          id="agent-boundaries"
          v-model="form.boundaries"
          type="textarea"
          :rows="2"
          maxlength="2000"
          placeholder="例如：不要替我直接改代码，先解释思路"
        />
      </div>

      <div class="field">
        <label for="agent-greeting">空态问候语</label>
        <el-input
          id="agent-greeting"
          v-model="form.greeting"
          maxlength="200"
          placeholder="例如：今天想推进哪一块？"
        />
      </div>

      <div class="form-actions">
        <el-button text @click="resetForm">撤销修改</el-button>
        <el-button
          type="primary"
          native-type="submit"
          :loading="identity.saving"
          :disabled="!canSave"
        >
          保存人格
        </el-button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import LoadingState from '../common/LoadingState.vue'
import ErrorState from '../common/ErrorState.vue'
import { useAgentIdentityStore } from '../../stores/agentIdentity'
import type { AgentProfilePayload } from '../../api/ai'

const identity = useAgentIdentityStore()

const form = reactive<AgentProfilePayload>({
  name: '',
  persona: '',
  tone: '严谨',
  expertise: '',
  boundaries: '',
  greeting: '',
})

const canSave = computed(() => Boolean(form.name.trim() && form.persona.trim()))

function syncForm(): void {
  const profile = identity.activeProfile
  form.name = profile?.name ?? '知识助手'
  form.persona = profile?.persona ?? '你的个人知识搭档，帮你梳理笔记与推进目标'
  form.tone = profile?.tone ?? '严谨'
  form.expertise = profile?.expertise ?? ''
  form.boundaries = profile?.boundaries ?? ''
  form.greeting = profile?.greeting ?? ''
}

watch(() => identity.activeProfile, syncForm, { immediate: true })

async function save(): Promise<void> {
  if (!canSave.value) return
  await identity.saveProfile({
    name: form.name.trim(),
    persona: form.persona.trim(),
    tone: form.tone,
    expertise: form.expertise?.trim() || null,
    boundaries: form.boundaries?.trim() || null,
    greeting: form.greeting?.trim() || null,
  })
  ElMessage.success('人格已保存')
}

function resetForm(): void {
  syncForm()
}

function reload(): Promise<void> {
  return identity.loadPanels()
}
</script>

<style scoped>
.identity-panel {
  min-height: 200px;
}

.profile-form {
  display: grid;
  gap: var(--rh-space-base);
}

.field {
  display: grid;
  gap: 7px;
}

.field label,
.field-label {
  color: var(--rh-text-secondary);
  font-size: var(--rh-fs-sm);
  font-weight: 700;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--rh-space-sm);
  padding-top: var(--rh-space-sm);
  border-top: 1px solid var(--rh-border-faint);
}
</style>

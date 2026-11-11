<template>
  <div class="rh-page rh-page--narrow">
    <LoadingState v-if="loading" variant="detail" />

    <ErrorState
      v-else-if="error"
      title="团队信息加载失败"
      description="团队可能已解散，或你没有访问权限"
      @retry="load"
    />

    <template v-else-if="team">
      <div class="team-header">
        <div class="team-heading">
          <button class="back-link" aria-label="返回团队列表" @click="router.push('/teams')">
            <el-icon><ArrowLeft /></el-icon>团队空间
          </button>
          <div class="title-row">
            <h1 class="page-title">{{ team.name }}</h1>
            <el-tag size="small" effect="plain">{{ roleLabel(team.role) }}</el-tag>
          </div>
          <p class="page-subtitle">{{ team.description || '暂无团队简介' }}</p>
        </div>

        <div class="header-actions">
          <el-button @click="copyInvite">
            <el-icon><CopyDocument /></el-icon>邀请码 {{ team.invite_code }}
          </el-button>
          <el-tooltip content="重置邀请码后，旧码立即失效" placement="top">
            <el-button v-if="canManage" aria-label="重置邀请码" @click="regenerateInvite">
              <el-icon><RefreshRight /></el-icon>
            </el-button>
          </el-tooltip>
          <el-button v-if="canManage" @click="openSettings">
            <el-icon><Setting /></el-icon>设置
          </el-button>
          <el-button v-if="team.role !== 'owner'" type="danger" plain @click="leaveTeam">退出团队</el-button>
        </div>
      </div>

      <div class="team-stats">
        <span>{{ team.member_count }} 位成员</span>
        <span>{{ team.note_count }} 篇笔记</span>
        <span>{{ team.prompt_count }} 条提示词</span>
      </div>

      <el-tabs v-model="activeTab" class="team-tabs">
        <el-tab-pane label="团队笔记" name="notes">
          <div class="pane-toolbar">
            <span class="pane-hint">团队成员可读，作者与管理员可编辑</span>
            <el-button type="primary" @click="openNoteDialog">
              <el-icon><Plus /></el-icon>新建团队笔记
            </el-button>
          </div>

          <LoadingState v-if="resourceLoading" variant="row" :count="3" />

          <ul v-else-if="notes.length" class="resource-list">
            <li
              v-for="note in notes"
              :key="note.id"
              class="resource-item"
              role="button"
              tabindex="0"
              :aria-label="`预览笔记「${note.title}」`"
              @click="openPreview(note)"
              @keydown.enter.prevent="openPreview(note)"
            >
              <div class="resource-main">
                <strong>{{ note.title }}</strong>
                <span class="resource-meta">
                  {{ note.owner_username || '成员' }} · 更新于 {{ formatRelative(note.updated_at) }}
                </span>
              </div>
              <div class="resource-tags">
                <el-tag v-for="tag in (note.tags || []).slice(0, 3)" :key="tag" size="small" effect="plain">{{ tag }}</el-tag>
              </div>
            </li>
          </ul>

          <EmptyState
            v-else
            :icon="Document"
            title="团队还没有笔记"
            description="把项目规范、会议纪要沉淀到这里，AI 问答会自动引用"
          >
            <el-button type="primary" @click="openNoteDialog">写第一篇</el-button>
          </EmptyState>
        </el-tab-pane>

        <el-tab-pane label="团队提示词" name="prompts">
          <div class="pane-toolbar">
            <span class="pane-hint">沉淀团队通用的提示词模板，变量可复用</span>
            <el-button type="primary" @click="openPromptDialog">
              <el-icon><Plus /></el-icon>新建团队提示词
            </el-button>
          </div>

          <LoadingState v-if="resourceLoading" variant="row" :count="3" />

          <ul v-else-if="prompts.length" class="resource-list">
            <li
              v-for="prompt in prompts"
              :key="prompt.id"
              class="resource-item"
              role="link"
              tabindex="0"
              :aria-label="`打开提示词「${prompt.title}」`"
              @click="router.push(`/prompts/${prompt.id}`)"
              @keydown.enter.prevent="router.push(`/prompts/${prompt.id}`)"
            >
              <div class="resource-main">
                <strong>{{ prompt.title }}</strong>
                <span class="resource-meta">
                  {{ prompt.owner_username || '成员' }} · 使用 {{ prompt.usage_count }} 次
                </span>
              </div>
              <p class="resource-desc">{{ prompt.description || '暂无简介' }}</p>
            </li>
          </ul>

          <EmptyState
            v-else
            :icon="MagicStick"
            title="团队还没有提示词"
            description="把高频使用的提法固定下来，减少重复调试"
          >
            <el-button type="primary" @click="openPromptDialog">新建第一条</el-button>
          </EmptyState>
        </el-tab-pane>

        <el-tab-pane :label="`成员 ${members.length}`" name="members">
          <ul class="member-list">
            <li v-for="member in members" :key="member.id" class="member-item">
              <el-avatar :size="34" :src="member.avatar || undefined">
                {{ member.username.charAt(0).toUpperCase() }}
              </el-avatar>
              <div class="member-main">
                <strong>{{ member.username }}</strong>
                <span class="resource-meta">加入于 {{ formatDate(member.joined_at) }}</span>
              </div>

              <el-select
                v-if="isOwner && member.role !== 'owner'"
                :model-value="member.role"
                size="small"
                class="role-select"
                :aria-label="`调整 ${member.username} 的角色`"
                @change="changeRole(member, $event)"
              >
                <el-option label="管理员" value="admin" />
                <el-option label="成员" value="member" />
              </el-select>
              <el-tag v-else size="small" effect="plain">{{ roleLabel(member.role) }}</el-tag>

              <el-button
                v-if="removable(member)"
                type="danger"
                link
                size="small"
                @click="removeMember(member)"
              >
                移除
              </el-button>
            </li>
          </ul>
        </el-tab-pane>
      </el-tabs>
    </template>

    <!-- 新建笔记 -->
    <el-dialog v-model="noteDialogVisible" title="新建团队笔记" width="640px" :close-on-click-modal="false">
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="标题" required>
          <el-input v-model="noteForm.title" maxlength="255" show-word-limit placeholder="例如：接口联调约定" />
        </el-form-item>
        <el-form-item label="正文（Markdown）">
          <el-input v-model="noteForm.content" type="textarea" :rows="10" placeholder="支持 Markdown 语法" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="noteDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitNote">保存</el-button>
      </template>
    </el-dialog>

    <!-- 新建提示词 -->
    <el-dialog v-model="promptDialogVisible" title="新建团队提示词" width="640px" :close-on-click-modal="false">
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="标题" required>
          <el-input v-model="promptForm.title" maxlength="255" show-word-limit placeholder="例如：Code Review 清单" />
        </el-form-item>
        <el-form-item label="简介">
          <el-input v-model="promptForm.description" maxlength="500" show-word-limit placeholder="这条提示词解决什么问题？" />
        </el-form-item>
        <el-form-item label="正文" required>
          <el-input v-model="promptForm.content" type="textarea" :rows="10" placeholder="支持 {{变量}} 占位符" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="promptDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitPrompt">保存</el-button>
      </template>
    </el-dialog>

    <!-- 团队设置 -->
    <el-dialog v-model="settingsVisible" title="团队设置" width="480px" :close-on-click-modal="false">
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="团队名称" required>
          <el-input v-model="settingsForm.name" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="团队简介">
          <el-input v-model="settingsForm.description" type="textarea" :rows="3" maxlength="500" show-word-limit />
        </el-form-item>
      </el-form>
      <div v-if="isOwner" class="danger-zone">
        <div>
          <strong>解散团队</strong>
          <p>团队成员将失去访问权限，资源回到各自作者的个人空间。</p>
        </div>
        <el-button type="danger" plain @click="deleteTeam">解散团队</el-button>
      </div>
      <template #footer>
        <el-button @click="settingsVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitSettings">保存</el-button>
      </template>
    </el-dialog>

    <!-- 笔记预览 -->
    <el-drawer v-model="previewVisible" :title="preview?.title || '笔记预览'" size="620px">
      <div class="preview-meta">
        <span>{{ preview?.owner_username || '成员' }}</span>
        <span v-if="preview">更新于 {{ formatDateTime(preview.updated_at) }}</span>
      </div>
      <div class="rh-markdown preview-body" v-html="previewHtml" />
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft,
  CopyDocument,
  Document,
  MagicStick,
  Plus,
  RefreshRight,
  Setting,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'
import { teamsApi } from '../../api/teams'
import type { Team, TeamMember, TeamRole } from '../../api/teams'
import { notesApi } from '../../api/notes'
import type { Note } from '../../api/notes'
import { promptsApi } from '../../api/prompts'
import type { Prompt } from '../../api/prompts'
import { getApiErrorMessage } from '../../api/http'
import { formatDate, formatDateTime, formatRelative } from '../../utils/format'
import EmptyState from '../../components/common/EmptyState.vue'
import ErrorState from '../../components/common/ErrorState.vue'
import LoadingState from '../../components/common/LoadingState.vue'

const route = useRoute()
const router = useRouter()

const md = new MarkdownIt({ html: false, linkify: true, typographer: true })

const teamId = computed(() => Number(route.params.id))
const team = ref<Team | null>(null)
const members = ref<TeamMember[]>([])
const notes = ref<Note[]>([])
const prompts = ref<Prompt[]>([])

const loading = ref(true)
const resourceLoading = ref(true)
const error = ref(false)
const submitting = ref(false)
const activeTab = ref<'notes' | 'prompts' | 'members'>('notes')

const noteDialogVisible = ref(false)
const noteForm = reactive({ title: '', content: '' })
const promptDialogVisible = ref(false)
const promptForm = reactive({ title: '', description: '', content: '' })

const settingsVisible = ref(false)
const settingsForm = reactive({ name: '', description: '' })

const previewVisible = ref(false)
const preview = ref<Note | null>(null)

const ROLE_LABELS: Record<TeamRole, string> = {
  owner: '创建者',
  admin: '管理员',
  member: '成员',
}

const isOwner = computed(() => team.value?.role === 'owner')
/** 创建者与管理员具备成员管理和团队设置权限 */
const canManage = computed(() => ['owner', 'admin'].includes(team.value?.role || ''))

function roleLabel(role: TeamRole): string {
  return ROLE_LABELS[role] || '成员'
}

/** 判断内容是否为 HTML（TipTap 富文本快照），否则按 Markdown 渲染 */
function isHtml(value: string): boolean {
  return /<[a-z][\s\S]*>/i.test(value)
}

const previewHtml = computed(() => {
  const raw = preview.value?.content || ''
  return DOMPurify.sanitize(isHtml(raw) ? raw : md.render(raw))
})

/** 团队详情与成员：任一失败视为整页加载失败 */
async function load() {
  loading.value = true
  error.value = false
  try {
    const [detail, memberList] = await Promise.all([
      teamsApi.get(teamId.value),
      teamsApi.members(teamId.value),
    ])
    team.value = detail
    members.value = memberList
    void loadResources()
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

/** 团队资源：笔记与提示词并行加载 */
async function loadResources() {
  resourceLoading.value = true
  try {
    const [notePage, promptPage] = await Promise.all([
      notesApi.list({ team_id: teamId.value, page_size: 50 }),
      promptsApi.list({ team_id: teamId.value, page_size: 50 }),
    ])
    notes.value = notePage.items
    prompts.value = promptPage.items
  } catch (err) {
    ElMessage.error(getApiErrorMessage(err, '团队资源加载失败'))
  } finally {
    resourceLoading.value = false
  }
}

function openNoteDialog() {
  noteForm.title = ''
  noteForm.content = ''
  noteDialogVisible.value = true
}

function openPromptDialog() {
  promptForm.title = ''
  promptForm.description = ''
  promptForm.content = ''
  promptDialogVisible.value = true
}

async function submitNote() {
  if (!noteForm.title.trim()) {
    ElMessage.warning('请填写笔记标题')
    return
  }
  submitting.value = true
  try {
    await notesApi.create({
      title: noteForm.title.trim(),
      content: noteForm.content,
      team_id: teamId.value,
    })
    noteDialogVisible.value = false
    ElMessage.success('团队笔记已创建')
    await Promise.all([loadResources(), refreshTeam()])
  } catch (err) {
    ElMessage.error(getApiErrorMessage(err, '创建笔记失败'))
  } finally {
    submitting.value = false
  }
}

async function submitPrompt() {
  if (!promptForm.title.trim() || !promptForm.content.trim()) {
    ElMessage.warning('请填写标题和正文')
    return
  }
  submitting.value = true
  try {
    await promptsApi.create({
      title: promptForm.title.trim(),
      description: promptForm.description.trim() || undefined,
      content: promptForm.content,
      team_id: teamId.value,
    })
    promptDialogVisible.value = false
    ElMessage.success('团队提示词已创建')
    await Promise.all([loadResources(), refreshTeam()])
  } catch (err) {
    ElMessage.error(getApiErrorMessage(err, '创建提示词失败'))
  } finally {
    submitting.value = false
  }
}

async function openPreview(note: Note) {
  try {
    preview.value = await notesApi.get(note.id)
    previewVisible.value = true
  } catch (err) {
    ElMessage.error(getApiErrorMessage(err, '笔记加载失败'))
  }
}

/** 仅刷新团队计数，不打断当前标签页 */
async function refreshTeam() {
  try {
    team.value = await teamsApi.get(teamId.value)
  } catch {
    // 计数刷新失败不影响主流程
  }
}

async function copyInvite() {
  if (!team.value) return
  try {
    await navigator.clipboard.writeText(team.value.invite_code)
    ElMessage.success('邀请码已复制')
  } catch {
    ElMessage.info(`邀请码：${team.value.invite_code}`)
  }
}

async function regenerateInvite() {
  try {
    await ElMessageBox.confirm('重置后旧邀请码立即失效，已加入的成员不受影响。', '重置邀请码', {
      type: 'warning',
      confirmButtonText: '重置',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    const result = await teamsApi.regenerateInvite(teamId.value)
    if (team.value) team.value.invite_code = result.invite_code
    ElMessage.success('邀请码已重置')
  } catch (err) {
    ElMessage.error(getApiErrorMessage(err, '重置邀请码失败'))
  }
}

function removable(member: TeamMember): boolean {
  if (member.role === 'owner') return false
  if (isOwner.value) return true
  // 管理员之间平级，只能移除普通成员
  return canManage.value && member.role === 'member'
}

async function changeRole(member: TeamMember, value: unknown) {
  const role = value === 'admin' ? 'admin' : 'member'
  try {
    await teamsApi.updateMemberRole(teamId.value, member.user_id, role)
    member.role = role
    ElMessage.success('成员角色已更新')
  } catch (err) {
    ElMessage.error(getApiErrorMessage(err, '角色更新失败'))
    await load()
  }
}

async function removeMember(member: TeamMember) {
  try {
    await ElMessageBox.confirm(`确定将「${member.username}」移出团队吗？`, '移除成员', {
      type: 'error',
      confirmButtonText: '移除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await teamsApi.removeMember(teamId.value, member.user_id)
    ElMessage.success('已移除该成员')
    await load()
  } catch (err) {
    ElMessage.error(getApiErrorMessage(err, '移除成员失败'))
  }
}

function openSettings() {
  if (!team.value) return
  settingsForm.name = team.value.name
  settingsForm.description = team.value.description || ''
  settingsVisible.value = true
}

async function submitSettings() {
  if (!settingsForm.name.trim()) {
    ElMessage.warning('请填写团队名称')
    return
  }
  submitting.value = true
  try {
    team.value = await teamsApi.update(teamId.value, {
      name: settingsForm.name.trim(),
      description: settingsForm.description.trim(),
    })
    settingsVisible.value = false
    ElMessage.success('团队信息已更新')
  } catch (err) {
    ElMessage.error(getApiErrorMessage(err, '保存失败'))
  } finally {
    submitting.value = false
  }
}

async function deleteTeam() {
  try {
    await ElMessageBox.confirm('解散后团队成员将失去访问权限，此操作不可恢复。', '解散团队', {
      type: 'error',
      confirmButtonText: '解散',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await teamsApi.remove(teamId.value)
    ElMessage.success('团队已解散')
    router.push('/teams')
  } catch (err) {
    ElMessage.error(getApiErrorMessage(err, '解散失败'))
  }
}

async function leaveTeam() {
  try {
    await ElMessageBox.confirm('退出后将无法访问该团队的共享资源。', '退出团队', {
      type: 'warning',
      confirmButtonText: '退出',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await teamsApi.leave(teamId.value)
    ElMessage.success('已退出团队')
    router.push('/teams')
  } catch (err) {
    ElMessage.error(getApiErrorMessage(err, '退出失败'))
  }
}

onMounted(load)

// 同一页面内切换团队时重新拉取，避免残留上一个团队的数据
watch(teamId, () => {
  if (Number.isFinite(teamId.value)) void load()
})
</script>

<style scoped>
.team-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 16px; }
.back-link { display: inline-flex; align-items: center; gap: 4px; margin-bottom: 10px; padding: 0; border: 0; background: transparent; color: var(--rh-text-tertiary); font-size: 12px; cursor: pointer; }
.back-link:hover { color: var(--rh-text-primary); }
.title-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.page-title { margin: 0; font-size: 24px; font-weight: 700; color: var(--rh-text-primary); }
.page-subtitle { margin: 8px 0 0; max-width: 620px; color: var(--rh-text-secondary); font-size: 13px; line-height: 1.7; }
.header-actions { display: flex; gap: 8px; flex-wrap: wrap; }

.team-stats { display: flex; gap: 18px; padding: 12px 16px; border: 1px solid var(--rh-border-faint); border-radius: var(--rh-radius-md); background: var(--rh-bg-subtle); color: var(--rh-text-tertiary); font-size: 12px; }
.team-tabs { margin-top: 20px; }

.pane-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
.pane-hint { color: var(--rh-text-tertiary); font-size: 12px; }

.resource-list, .member-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.resource-item { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 14px 16px; border: 1px solid var(--rh-border-faint); border-radius: var(--rh-radius-md); background: var(--rh-bg-card); cursor: pointer; transition: border-color .18s ease, background .18s ease; }
.resource-item:hover, .resource-item:focus-visible { border-color: var(--rh-border-strong); background: var(--rh-bg-hover); }
.resource-main { min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.resource-main strong { color: var(--rh-text-primary); font-size: 14px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.resource-meta { color: var(--rh-text-tertiary); font-size: 12px; }
.resource-desc { margin: 0; max-width: 320px; color: var(--rh-text-secondary); font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.resource-tags { display: flex; gap: 6px; flex: 0 0 auto; }

.member-item { display: flex; align-items: center; gap: 12px; padding: 12px 16px; border: 1px solid var(--rh-border-faint); border-radius: var(--rh-radius-md); background: var(--rh-bg-card); }
.member-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.member-main strong { color: var(--rh-text-primary); font-size: 14px; font-weight: 600; }
.role-select { width: 108px; }

.danger-zone { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-top: 8px; padding: 14px 16px; border: 1px solid var(--rh-danger-border, var(--rh-border)); border-radius: var(--rh-radius-md); background: var(--rh-bg-subtle); }
.danger-zone strong { color: var(--rh-danger); font-size: 13px; }
.danger-zone p { margin: 4px 0 0; color: var(--rh-text-tertiary); font-size: 12px; line-height: 1.6; }

.preview-meta { display: flex; gap: 14px; margin-bottom: 16px; color: var(--rh-text-tertiary); font-size: 12px; }
.preview-body { color: var(--rh-text-primary); font-size: 14px; line-height: 1.8; }

@media (max-width: 640px) {
  .page-title { font-size: 20px; }
  .header-actions { width: 100%; }
  .resource-item { flex-direction: column; align-items: flex-start; }
  .resource-desc { max-width: 100%; }
}
</style>

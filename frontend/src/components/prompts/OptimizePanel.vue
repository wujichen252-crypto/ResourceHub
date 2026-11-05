<template>
  <el-drawer
    v-model="drawerVisible"
    title="AI 自动优化"
    size="min(760px, 100vw)"
    @open="onOpen"
    @close="stopPolling"
  >
    <div v-if="phase === 'loading'" class="panel-center">
      <el-skeleton :rows="6" animated />
    </div>

    <!-- 还没有评测集：引导先去实验室建一个 -->
    <div v-else-if="phase === 'no-suite'" class="panel-center">
      <el-empty description="自动优化依赖评测集打分，请先为这个提示词创建评测集">
        <el-button type="primary" @click="goLab">去测试实验室创建</el-button>
      </el-empty>
    </div>

    <!-- 配置表单 -->
    <div v-else-if="phase === 'config'" class="config-form">
      <el-form label-position="top">
        <el-form-item label="评测集（打分依据）">
          <el-select v-model="suiteId" placeholder="选择评测集" class="w-full">
            <el-option
              v-for="s in suites"
              :key="s.id"
              :label="`${s.name}（${s.case_count} 个用例）`"
              :value="s.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="优化基准版本（可选，默认当前正文）">
          <el-select v-model="baselineVersionId" placeholder="当前正文" clearable class="w-full">
            <el-option
              v-for="v in promptsStore.versions"
              :key="v.id"
              :label="`v${v.version_number} · ${v.message || '无描述'}`"
              :value="v.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item :label="`最大优化轮数：${maxRounds} 轮`">
          <el-slider v-model="maxRounds" :min="1" :max="5" show-stops />
        </el-form-item>

        <el-form-item :label="`达标分数线：${scoreThreshold} 分（达到即提前结束）`">
          <el-input-number v-model="scoreThreshold" :min="60" :max="100" :step="5" />
        </el-form-item>

        <el-form-item :label="`改写模型温度：${temperature.toFixed(1)}（越低越保守）`">
          <el-slider v-model="temperature" :min="0" :max="1" :step="0.1" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" class="w-full" :loading="starting" @click="handleStart">
            <el-icon><MagicStick /></el-icon> 开始优化
          </el-button>
        </el-form-item>
      </el-form>
      <p class="config-hint">
        流程：先对基线跑一遍评测集打分 → AI 根据低分用例的诊断改写提示词 → 再用同一套用例复评。
        全程约每轮 1-3 分钟，结束后由你决定是否采纳。
      </p>
    </div>

    <!-- 执行中：轮询状态 -->
    <div v-else-if="phase === 'running'" class="panel-center">
      <div class="running-box">
        <p class="running-title">第 {{ run?.round_number ?? '-' }} / {{ run?.max_rounds ?? '-' }} 轮优化执行中…</p>
        <el-progress :percentage="runProgress" :stroke-width="8" />
        <p class="running-sub">基线评测 → AI 诊断改写 → 候选评测，请保持页面打开</p>
        <p v-if="run?.total_tokens" class="running-tokens">本轮已消耗 {{ run.total_tokens }} tokens</p>
        <el-button plain type="danger" @click="handleCancel">放弃本次优化</el-button>
      </div>
    </div>

    <!-- 待决策：对比报告 -->
    <div v-else-if="phase === 'review' && run" class="review-layout">
      <div class="score-compare">
        <div class="score-cell">
          <span class="score-label">基线得分</span>
          <span class="score-value">{{ formatScore(run.baseline_score) }}</span>
        </div>
        <div class="score-arrow">
          <el-icon><Right /></el-icon>
          <el-tag
            v-if="scoreDelta !== null && scoreDelta !== 0"
            :type="scoreDelta > 0 ? 'success' : 'danger'"
            size="small"
          >
            {{ scoreDelta > 0 ? '+' : '' }}{{ scoreDelta }}
          </el-tag>
        </div>
        <div class="score-cell candidate">
          <span class="score-label">候选得分</span>
          <span class="score-value">{{ formatScore(run.candidate_score) }}</span>
        </div>
      </div>

      <div v-if="run.analysis" class="report-block">
        <h4 class="block-title">问题诊断</h4>
        <p class="block-text">{{ run.analysis }}</p>
      </div>
      <div v-if="run.changelog" class="report-block">
        <h4 class="block-title">改动说明</h4>
        <p class="block-text">{{ run.changelog }}</p>
      </div>

      <!-- 正文行级对比 -->
      <div class="report-block">
        <div class="block-header">
          <h4 class="block-title">正文对比</h4>
          <span class="diff-summary">
            <span v-if="stats.added" class="summary-add">新增 {{ stats.added }} 行</span>
            <span v-if="stats.removed" class="summary-del">删除 {{ stats.removed }} 行</span>
            <span v-if="!stats.added && !stats.removed" class="summary-same">正文没有变化</span>
          </span>
        </div>
        <div class="diff-lines">
          <div
            v-for="(seg, i) in segments"
            :key="i"
            class="diff-line"
            :class="'diff-' + seg.type"
          >
            <span class="diff-marker">{{ seg.type === 'insert' ? '+' : seg.type === 'delete' ? '-' : ' ' }}</span>
            <span class="diff-text">{{ seg.value || ' ' }}</span>
          </div>
        </div>
      </div>

      <!-- 逐用例对比 -->
      <el-collapse v-if="caseRows.length" class="case-collapse">
        <el-collapse-item :title="`逐用例对比（${caseRows.length} 个用例）`">
          <div v-for="row in caseRows" :key="row.case_id" class="case-row">
            <div class="case-head">
              <span class="case-id">用例 #{{ row.case_id }}</span>
              <span class="case-score" :class="row.deltaClass">
                {{ formatScore(row.before) }} → {{ formatScore(row.after) }}
              </span>
            </div>
            <p v-if="row.reason" class="case-reason">{{ row.reason }}</p>
          </div>
        </el-collapse-item>
      </el-collapse>

      <!-- 历史轮次 -->
      <el-collapse v-if="rounds.length > 1" class="case-collapse">
        <el-collapse-item :title="`历史轮次（${rounds.length} 轮）`">
          <div v-for="r in rounds" :key="r.id" class="case-row">
            <div class="case-head">
              <span class="case-id">第 {{ r.round_number }} 轮</span>
              <span class="case-score">{{ formatScore(r.candidate_score) }}</span>
            </div>
            <p v-if="r.changelog" class="case-reason">{{ r.changelog }}</p>
          </div>
        </el-collapse-item>
      </el-collapse>

      <div class="review-actions">
        <el-button plain type="danger" @click="handleCancel">放弃</el-button>
        <el-button
          v-if="run.round_number < run.max_rounds"
          plain
          :loading="iterating"
          @click="handleIterate"
        >再优化一轮（{{ run.round_number }}/{{ run.max_rounds }}）</el-button>
        <el-button type="primary" :loading="accepting" @click="handleAccept">
          <el-icon><Select /></el-icon> 采纳为新版本
        </el-button>
      </div>
    </div>

    <!-- 已采纳 -->
    <div v-else-if="phase === 'completed'" class="panel-center">
      <el-result icon="success" title="已采纳为新版本">
        <template #sub-title>
          <p>v{{ acceptedVersion?.version_number }} · {{ acceptedVersion?.message || 'AI 自动优化' }}</p>
          <p>原正文已自动快照，可随时在版本历史中回滚</p>
        </template>
        <template #extra>
          <el-button @click="emit('view-versions')">查看版本历史</el-button>
          <el-button type="primary" @click="resetToConfig">继续优化</el-button>
        </template>
      </el-result>
    </div>

    <!-- 失败 / 已取消 -->
    <div v-else-if="phase === 'failed' || phase === 'cancelled'" class="panel-center">
      <el-result
        :icon="phase === 'failed' ? 'error' : 'info'"
        :title="phase === 'failed' ? '优化失败' : '已放弃优化'"
        :sub-title="run?.error_message || ''"
      >
        <template #extra>
          <el-button type="primary" @click="resetToConfig">重新配置</el-button>
        </template>
      </el-result>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, ref, watch, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { MagicStick, Right, Select } from '@element-plus/icons-vue'
import { evalApi, type EvalSuite } from '../../api/eval'
import {
  optimizerApi,
  type OptimizationRun,
  type OptimizationRound,
  type AcceptedVersion,
  type OptimizationRunStatus,
} from '../../api/optimizer'
import { usePromptsStore } from '../../stores/prompts'
import { diffLines, diffStats, type DiffSegment } from '../../utils/diff'

const props = defineProps<{
  modelValue: boolean
  promptId: number | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  /** 候选已采纳为新版本，父组件需刷新正文 */
  accepted: []
  /** 用户想去看版本历史 */
  'view-versions': []
}>()

const router = useRouter()
const promptsStore = usePromptsStore()

type Phase =
  | 'loading'
  | 'no-suite'
  | 'config'
  | 'running'
  | 'review'
  | 'completed'
  | 'failed'
  | 'cancelled'

const drawerVisible = ref(props.modelValue)
const phase = ref<Phase>('loading')
const suites = ref<EvalSuite[]>([])
const rounds = ref<OptimizationRound[]>([])
const run = ref<OptimizationRun | null>(null)
const acceptedVersion = ref<AcceptedVersion | null>(null)

const suiteId = ref<number | null>(null)
const baselineVersionId = ref<number | null>(null)
const maxRounds = ref(3)
const scoreThreshold = ref(80)
const temperature = ref(0.3)

const starting = ref(false)
const accepting = ref(false)
const iterating = ref(false)
let pollTimer: ReturnType<typeof setInterval> | null = null

/** 正文行级对比段与增删统计 */
const segments = computed<DiffSegment[]>(() => {
  if (!run.value?.baseline_content || !run.value?.candidate_content) return []
  return diffLines(run.value.baseline_content, run.value.candidate_content)
})
const stats = computed(() => diffStats(segments.value))

/** 候选相对基线的分数差 */
const scoreDelta = computed(() => {
  const b = run.value?.baseline_score
  const c = run.value?.candidate_score
  if (b === null || b === undefined || c === null || c === undefined) return null
  return Math.round(c - b)
})

/** 执行中的粗略进度：按轮次推进估算 */
const runProgress = computed(() => {
  if (!run.value) return 0
  return Math.min(95, Math.round(((run.value.round_number) / run.value.max_rounds) * 90 + 10))
})

/** 逐用例对比行：按 case_id 关联基线与候选两次评测 */
const caseRows = computed(() => {
  const before = run.value?.baseline_detail?.results ?? []
  const after = run.value?.candidate_detail?.results ?? []
  const afterMap = new Map(after.map((r) => [r.case_id, r]))
  return before
    .filter((r) => afterMap.has(r.case_id))
    .map((r) => {
      const next = afterMap.get(r.case_id)!
      const b = r.score
      const c = next.score
      let deltaClass = ''
      if (b !== null && c !== null && c > b) deltaClass = 'is-up'
      else if (b !== null && c !== null && c < b) deltaClass = 'is-down'
      return {
        case_id: r.case_id,
        before: b,
        after: c,
        reason: next.judge_reason,
        deltaClass,
      }
    })
})

watch(() => props.modelValue, (v) => { drawerVisible.value = v })
watch(drawerVisible, (v) => emit('update:modelValue', v))

function formatScore(score: number | null | undefined): string {
  return score === null || score === undefined ? '—' : `${Math.round(score)} 分`
}

async function onOpen() {
  if (!props.promptId) return
  phase.value = 'loading'
  rounds.value = []
  run.value = null
  acceptedVersion.value = null
  try {
    const [suiteRes] = await Promise.all([
      evalApi.suites(props.promptId),
      promptsStore.fetchVersions(props.promptId).catch(() => undefined),
    ])
    const runsRes: { items: OptimizationRun[] } | null = await optimizerApi
      .listRuns(props.promptId)
      .catch(() => null)
    suites.value = suiteRes.items
    if (suites.value.length === 0) {
      phase.value = 'no-suite'
      return
    }

    // 恢复进行中/待决策的会话：后台任务不随抽屉关闭而中止，重开面板要能接上
    const active = runsRes?.items.find(
      (r) => r.status === 'running' || r.status === 'awaiting_review',
    )
    if (active) {
      run.value = active
      suiteId.value = active.suite_id
      if (active.status === 'running') {
        startPolling()
        phase.value = 'running'
      } else {
        await loadRounds()
        phase.value = 'review'
      }
      return
    }

    suiteId.value = suites.value[0].id
    baselineVersionId.value = null
    phase.value = 'config'
  } catch {
    ElMessage.error('评测集加载失败，请稍后重试')
    phase.value = 'no-suite'
  }
}

function goLab() {
  drawerVisible.value = false
  if (props.promptId) router.push(`/prompts/${props.promptId}/lab`)
}

async function handleStart() {
  if (!props.promptId || !suiteId.value) return
  starting.value = true
  try {
    run.value = await optimizerApi.startRun({
      prompt_id: props.promptId,
      suite_id: suiteId.value,
      prompt_version_id: baselineVersionId.value,
      max_rounds: maxRounds.value,
      score_threshold: scoreThreshold.value,
      temperature: temperature.value,
    })
    startPolling()
    phase.value = 'running'
  } catch {
    // 错误提示由 http 拦截器统一弹出
  } finally {
    starting.value = false
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(pollStatus, 2000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function pollStatus() {
  if (!run.value) return
  try {
    const next = await optimizerApi.getStatus(run.value.id)
    run.value = next
    const status = next.status as OptimizationRunStatus
    if (status === 'running') return
    stopPolling()
    await loadRounds()
    if (status === 'awaiting_review') phase.value = 'review'
    else if (status === 'completed') phase.value = 'completed'
    else if (status === 'failed') phase.value = 'failed'
    else if (status === 'cancelled') phase.value = 'cancelled'
  } catch {
    // 轮询瞬时失败不中断，等下一轮
  }
}

async function loadRounds() {
  if (!run.value) return
  try {
    const res = await optimizerApi.listRounds(run.value.id)
    rounds.value = res.items
  } catch {
    rounds.value = []
  }
}

async function handleIterate() {
  if (!run.value) return
  iterating.value = true
  try {
    run.value = await optimizerApi.iterate(run.value.id)
    rounds.value = []
    startPolling()
    phase.value = 'running'
  } catch {
    // 拦截器已提示
  } finally {
    iterating.value = false
  }
}

async function handleAccept() {
  if (!run.value) return
  try {
    await ElMessageBox.confirm(
      '采纳后 AI 候选内容将写入新版本并更新提示词正文，原正文会自动快照。',
      '确认采纳',
      { confirmButtonText: '采纳', cancelButtonText: '再想想', type: 'warning' },
    )
  } catch {
    return
  }
  accepting.value = true
  try {
    const result = await optimizerApi.accept(run.value.id)
    acceptedVersion.value = result.new_version
    phase.value = 'completed'
    emit('accepted')
  } catch {
    // 拦截器已提示
  } finally {
    accepting.value = false
  }
}

async function handleCancel() {
  if (!run.value) return
  stopPolling()
  try {
    run.value = await optimizerApi.cancel(run.value.id)
    phase.value = 'cancelled'
  } catch {
    // 拦截器已提示
  }
}

function resetToConfig() {
  run.value = null
  acceptedVersion.value = null
  rounds.value = []
  phase.value = 'config'
}

onBeforeUnmount(stopPolling)
</script>

<style scoped>
.panel-center {
  padding: 40px 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.w-full {
  width: 100%;
}

.config-hint {
  font-size: 13px;
  line-height: 1.7;
  color: var(--rh-text-tertiary);
  background: var(--rh-bg-inset);
  border-radius: var(--rh-radius-sm);
  padding: 12px 14px;
}

/* ── 执行中 ── */

.running-box {
  text-align: center;
  max-width: 360px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  align-items: stretch;
}

.running-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--rh-text-primary);
}

.running-sub {
  font-size: 13px;
  color: var(--rh-text-tertiary);
}

.running-tokens {
  font-size: 12px;
  color: var(--rh-text-tertiary);
}

/* ── 对比报告 ── */

.review-layout {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.score-compare {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: var(--rh-bg-inset);
  border-radius: var(--rh-radius-md);
}

.score-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  min-width: 96px;
}

.score-cell.candidate .score-value {
  color: var(--rh-primary);
}

.score-label {
  font-size: 12px;
  color: var(--rh-text-tertiary);
}

.score-value {
  font-size: 26px;
  font-weight: 700;
  color: var(--rh-text-primary);
  font-variant-numeric: tabular-nums;
}

.score-arrow {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--rh-text-tertiary);
}

.report-block {
  border: 1px solid var(--rh-border-light);
  border-radius: var(--rh-radius-md);
  padding: 12px 14px;
}

.block-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.block-title {
  margin: 0 0 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--rh-text-secondary);
}

.block-header .block-title {
  margin-bottom: 0;
}

.block-text {
  margin: 0;
  font-size: 14px;
  line-height: 1.7;
  color: var(--rh-text-primary);
}

.diff-summary {
  display: flex;
  gap: 8px;
  font-size: 12px;
}

.summary-add {
  color: var(--rh-success-strong);
  background: var(--rh-success-subtle);
  padding: 1px 6px;
  border-radius: var(--rh-radius-xs);
}

.summary-del {
  color: var(--rh-danger);
  background: var(--rh-danger-subtle);
  padding: 1px 6px;
  border-radius: var(--rh-radius-xs);
}

.summary-same {
  color: var(--rh-text-tertiary);
}

.diff-lines {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 13px;
  line-height: 1.6;
}

.diff-line {
  display: flex;
  padding: 1px 4px;
  border-radius: 2px;
}

.diff-marker {
  width: 16px;
  flex-shrink: 0;
  color: var(--rh-text-tertiary);
  user-select: none;
}

.diff-text {
  flex: 1;
  white-space: pre-wrap;
  word-break: break-all;
}

/* 增删行除颜色外叠加左侧色条，避免红绿色觉障碍下无法区分 */
.diff-insert {
  background: var(--rh-success-subtle);
  box-shadow: inset 2px 0 0 var(--rh-success-strong);
}

.diff-insert .diff-marker {
  color: var(--rh-success-strong);
}

.diff-delete {
  background: var(--rh-danger-subtle);
  box-shadow: inset 2px 0 0 var(--rh-danger);
}

.diff-delete .diff-marker {
  color: var(--rh-danger);
}

/* ── 逐用例 / 历史轮次 ── */

.case-collapse {
  border-top: 1px solid var(--rh-border-light);
  border-bottom: 1px solid var(--rh-border-light);
}

.case-row {
  padding: 8px 4px;
  border-bottom: 1px dashed var(--rh-border-faint);
}

.case-row:last-child {
  border-bottom: none;
}

.case-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.case-id {
  font-size: 13px;
  font-weight: 600;
  color: var(--rh-text-primary);
}

.case-score {
  font-size: 13px;
  color: var(--rh-text-secondary);
  font-variant-numeric: tabular-nums;
}

.case-score.is-up {
  color: var(--rh-success-strong);
}

.case-score.is-down {
  color: var(--rh-danger);
}

.case-reason {
  margin: 4px 0 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--rh-text-tertiary);
}

/* ── 决策按钮 ── */

.review-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 4px;
}
</style>

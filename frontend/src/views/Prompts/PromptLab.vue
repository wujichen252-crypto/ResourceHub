<template>
  <div class="rh-page rh-page--narrow lab-page">
    <header class="lab-head">
      <div>
        <el-button text class="back" @click="goBack">
          <el-icon><ArrowLeft /></el-icon> 返回提示词
        </el-button>
        <h1>提示词实验室</h1>
        <p class="sub">
          {{ prompt?.title || '加载中' }}
          <span v-if="prompt" class="sub-meta">· 一次生成多份回答，由评审 AI 打分，还能和历史版本对比</span>
        </p>
      </div>
      <el-button type="primary" :disabled="!prompt" @click="openCreate">
        <el-icon><Plus /></el-icon> 新建测试集
      </el-button>
    </header>

    <LoadingState v-if="loading" variant="detail" />
    <ErrorState
      v-else-if="loadError"
      title="测试页面加载失败"
      :description="loadError"
      @retry="loadAll"
    />
    <div v-else class="lab-body">
      <!-- 评测集列表 -->
      <aside class="suite-rail" aria-label="测试集列表">
        <p class="rail-title">测试集</p>
        <EmptyState
          v-if="!suites.length"
          :icon="Collection"
          title="还没有测试集"
          description="创建一组测试题目，看看改动后回答是否真的变好"
          min-height="0"
        />
        <ul v-else class="suite-list">
          <li v-for="suite in suites" :key="suite.id">
            <button
              class="suite-item"
              :class="{ active: suite.id === activeSuiteId }"
              :aria-current="suite.id === activeSuiteId ? 'true' : undefined"
              @click="activeSuiteId = suite.id"
            >
              <span class="suite-name">{{ suite.name }}</span>
              <span class="suite-count">{{ suite.case_count }} 道题</span>
            </button>
            <el-button
              text
              class="suite-del"
              :aria-label="`删除测试集：${suite.name}`"
              @click.stop="removeSuite(suite)"
            >
              <el-icon><Delete /></el-icon>
            </el-button>
          </li>
        </ul>
      </aside>

      <!-- 主体 -->
      <section class="lab-main">
        <EmptyState
          v-if="!activeSuite"
          :icon="DataAnalysis"
          title="选择一个测试集"
          description="每个测试集包含若干道题，运行后给出每道题的得分和平均分"
          min-height="360px"
        />

        <template v-else>
          <div class="suite-head">
            <div>
              <h2>{{ activeSuite.name }}</h2>
              <p v-if="activeSuite.description" class="suite-desc">{{ activeSuite.description }}</p>
              <p class="suite-meta">
                评审 AI 会为每道题的回答打分 · 共 {{ activeSuite.case_count }} 道题
              </p>
            </div>
            <el-tag v-if="latestRun" effect="plain" size="small">
              最近一次平均分 {{ formatScore(latestRun.avg) }}
            </el-tag>
          </div>

          <!-- 运行控制 -->
          <div class="run-bar">
            <el-select
              v-model="versionId"
              class="run-version"
              placeholder="对比版本"
              aria-label="选择要测试的提示词版本"
            >
              <el-option :value="null" label="当前版本" />
              <el-option
                v-for="version in versions"
                :key="version.id"
                :value="version.id"
                :label="`v${version.version_number}（${version.message || '历史版本'}）`"
              />
            </el-select>
            <span class="run-temp-label">
              创意程度
              <span class="run-temp-note">（数值越高回答越灵活，越低越稳定）</span>
            </span>
            <el-input-number
              v-model="temperature"
              :min="0"
              :max="2"
              :step="0.1"
              :precision="1"
              aria-label="创意程度"
            />
            <el-button type="primary" :loading="running" @click="runSuite">
              <el-icon v-if="!running"><VideoPlay /></el-icon>
              {{ running ? '测试中…' : '开始测试' }}
            </el-button>
          </div>

          <p v-if="running" class="run-hint" role="status">
            正在逐题生成并评分，可能需要几十秒，请先不要关闭页面
          </p>

          <ErrorState
            v-if="resultError"
            title="测试失败"
            :description="resultError"
            :retryable="false"
          />

          <!-- 最近一次结果 -->
          <section v-if="latestRun" class="result-block" aria-label="最近一次测试结果">
            <div class="result-head">
              <div class="score-board">
                <span class="score-num">{{ formatScore(latestRun.avg) }}</span>
                <span class="score-label">平均分</span>
              </div>
              <div class="result-meta">
                <span>{{ latestRun.items.length }} 道题</span>
                <span>版本 {{ latestRun.versionNumber === null ? '当前' : `v${latestRun.versionNumber}` }}</span>
                <span>{{ latestRun.created ? formatDateTime(latestRun.created) : '' }}</span>
              </div>
            </div>

            <article
              v-for="item in latestRun.items"
              :key="item.id"
              class="case-card"
            >
              <div class="case-head">
                <div class="case-vars">
                  <el-tag
                    v-for="(value, key) in item.variables"
                    :key="key"
                    size="small"
                    effect="plain"
                  >
                    {{ key }}：{{ value || '（空）' }}
                  </el-tag>
                  <span v-if="!Object.keys(item.variables).length" class="case-no-var">没有待填内容</span>
                </div>
                <span class="case-score" :class="scoreClass(item.score)">
                  {{ item.score === null ? '未评分' : item.score }}
                </span>
              </div>
              <p v-if="item.judge_reason" class="case-reason">{{ item.judge_reason }}</p>
              <details class="case-output">
                <summary>查看回答（用量 {{ item.total_tokens }} · 用时 {{ item.latency_ms }} 毫秒）</summary>
                <pre>{{ item.output }}</pre>
              </details>
            </article>
          </section>

          <EmptyState
            v-else
            :icon="VideoPlay"
            title="还没有测试记录"
            description="选好版本后点开始测试，结果会保存下来方便前后对比"
            min-height="240px"
          />

          <!-- 历史记录 -->
          <section v-if="historyRuns.length" class="history-block">
            <h3>历史记录</h3>
            <ul class="history-list">
              <li v-for="run in historyRuns" :key="run.created || run.items[0].id" class="history-item">
                <span class="history-time">{{ run.created ? formatDateTime(run.created) : '未知时间' }}</span>
                <span class="history-version">版本 {{ run.versionNumber === null ? '当前' : `v${run.versionNumber}` }}</span>
                <span class="history-cases">{{ run.items.length }} 道题</span>
                <span class="history-score" :class="scoreClass(run.avg)">{{ formatScore(run.avg) }}</span>
              </li>
            </ul>
          </section>
        </template>
      </section>
    </div>

    <!-- 新建评测集 -->
    <el-dialog v-model="createVisible" title="新建测试集" width="720px" class="lab-dialog">
      <el-form label-width="84px" label-position="left">
        <el-form-item label="名称" required>
          <el-input v-model="createForm.name" maxlength="191" placeholder="如：答辩问答测试" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="createForm.description" maxlength="500" placeholder="这组测试题目想验证什么" />
        </el-form-item>
        <el-form-item label="测试题目">
          <div class="case-editor">
            <div v-for="(item, index) in createForm.cases" :key="index" class="case-editor__item">
              <div class="case-editor__head">
                <strong>题目 {{ index + 1 }}</strong>
                <el-button
                  v-if="createForm.cases.length > 1"
                  text
                  :aria-label="`删除题目 ${index + 1}`"
                  @click="createForm.cases.splice(index, 1)"
                >
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
              <div v-if="prompt?.variables.length" class="var-grid">
                <label v-for="name in prompt.variables" :key="name" class="var-field">
                  <span>{{ name }}</span>
                  <el-input v-model="item.variables[name]" :placeholder="`请输入 ${name} 的内容`" />
                </label>
              </div>
              <p v-else class="no-var-hint">这个提示词没有需要填写的内容，题目会直接使用原文</p>
              <el-input
                v-model="item.rubric"
                type="textarea"
                :rows="2"
                maxlength="2000"
                placeholder="评分要点（填写后才会让评审 AI 打分）"
              />
              <el-input
                v-model="item.expectedOutput"
                type="textarea"
                :rows="2"
                maxlength="4000"
                placeholder="期望的回答（可选，帮助评审 AI 判断）"
              />
            </div>
            <el-button text :disabled="createForm.cases.length >= 10" @click="addCase">
              <el-icon><Plus /></el-icon> 添加题目
            </el-button>
            <p class="case-limit">最多 10 道题；没填评分要点的题目只记录回答、不打分。</p>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
/**
 * 提示词实验室：按用例批量生成 + 评委模型打分，并留档结果做版本对比。
 * 与 PromptDetail 共用路由前缀，返回时恢复列表浏览位置由浏览器历史负责。
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft,
  Collection,
  DataAnalysis,
  Delete,
  Plus,
  VideoPlay,
} from '@element-plus/icons-vue'
import { promptsApi, type Prompt, type PromptVersion } from '../../api/prompts'
import { evalApi, type EvalResultRecord, type EvalSuite } from '../../api/eval'
import { getApiErrorMessage } from '../../api/http'
import EmptyState from '../../components/common/EmptyState.vue'
import ErrorState from '../../components/common/ErrorState.vue'
import LoadingState from '../../components/common/LoadingState.vue'
import { formatDateTime } from '../../utils/format'

interface CaseDraft {
  variables: Record<string, string>
  rubric: string
  expectedOutput: string
}

interface RunGroup {
  created: string | null
  versionNumber: number | null
  avg: number | null
  items: EvalResultRecord[]
}

const route = useRoute()
const router = useRouter()
const promptId = Number(route.params.id)

const loading = ref(true)
const loadError = ref<string | null>(null)
const prompt = ref<Prompt | null>(null)
const versions = ref<PromptVersion[]>([])

const suites = ref<EvalSuite[]>([])
const activeSuiteId = ref<number | null>(null)

const records = ref<EvalResultRecord[]>([])
const running = ref(false)
const resultError = ref<string | null>(null)

const versionId = ref<number | null>(null)
const temperature = ref(0.3)

const createVisible = ref(false)
const creating = ref(false)
const createForm = reactive<{
  name: string
  description: string
  cases: CaseDraft[]
}>({
  name: '',
  description: '',
  cases: [emptyCase()],
})

const activeSuite = computed(() => suites.value.find((item) => item.id === activeSuiteId.value) || null)

/** 按 created_at 聚合成一次运行，倒序排列 */
const runs = computed<RunGroup[]>(() => {
  const groups = new Map<string, EvalResultRecord[]>()
  for (const item of records.value) {
    const key = item.created_at || `unknown-${item.id}`
    const bucket = groups.get(key)
    if (bucket) bucket.push(item)
    else groups.set(key, [item])
  }
  return Array.from(groups.values()).map((items) => {
    const sorted = [...items].sort((a, b) => a.case_id - b.case_id)
    return {
      created: sorted[0].created_at,
      versionNumber: sorted[0].version_number,
      avg: averageScore(sorted),
      items: sorted,
    }
  })
})

const latestRun = computed(() => runs.value[0] || null)
const historyRuns = computed(() => runs.value.slice(1))

function emptyCase(): CaseDraft {
  return { variables: {}, rubric: '', expectedOutput: '' }
}

/** 均分只统计有分数的用例 */
function averageScore(items: EvalResultRecord[]): number | null {
  const scored = items.filter((item) => item.score !== null)
  if (!scored.length) return null
  return Number((scored.reduce((sum, item) => sum + (item.score || 0), 0) / scored.length).toFixed(1))
}

function formatScore(score: number | null): string {
  return score === null ? '—' : String(score)
}

function scoreClass(score: number | null): string {
  if (score === null) return 'is-none'
  if (score >= 80) return 'is-good'
  if (score >= 60) return 'is-mid'
  return 'is-bad'
}

async function loadAll(): Promise<void> {
  loading.value = true
  loadError.value = null
  try {
    const [detail, versionList, suiteList] = await Promise.all([
      promptsApi.get(promptId),
      promptsApi.getVersions(promptId),
      evalApi.suites(promptId),
    ])
    prompt.value = detail
    versions.value = versionList
    suites.value = suiteList.items
    // 赋值会触发 activeSuiteId 的 watch，由它拉取该评测集的历史结果
    activeSuiteId.value = suiteList.items[0]?.id ?? null
  } catch (err) {
    loadError.value = getApiErrorMessage(err, '无法加载提示词信息')
  } finally {
    loading.value = false
  }
}

async function loadResults(): Promise<void> {
  if (!activeSuiteId.value) {
    records.value = []
    return
  }
  try {
    const response = await evalApi.results(activeSuiteId.value)
    records.value = response.items
  } catch (err) {
    resultError.value = getApiErrorMessage(err, '无法加载测试结果')
  }
}

function openCreate(): void {
  createForm.name = ''
  createForm.description = ''
  createForm.cases = [emptyCase()]
  createVisible.value = true
}

function addCase(): void {
  createForm.cases.push(emptyCase())
}

async function submitCreate(): Promise<void> {
  if (!createForm.name.trim()) {
    ElMessage.warning('请填写测试集名称')
    return
  }
  creating.value = true
  try {
    const suite = await evalApi.createSuite({
      prompt_id: promptId,
      name: createForm.name.trim(),
      description: createForm.description.trim() || null,
      cases: createForm.cases.map((item) => ({
        variables: Object.fromEntries(
          Object.entries(item.variables).map(([key, value]) => [key, value.trim()]),
        ),
        rubric: item.rubric.trim() || null,
        expected_output: item.expectedOutput.trim() || null,
      })),
    })
    suites.value.unshift(suite)
    activeSuiteId.value = suite.id
    createVisible.value = false
    records.value = []
    ElMessage.success('测试集已创建')
  } catch {
    // http 拦截器已提示错误
  } finally {
    creating.value = false
  }
}

async function removeSuite(suite: EvalSuite): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `删除测试集「${suite.name}」后，它的历史结果也会一并清除，且无法恢复。`,
      '删除测试集',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await evalApi.deleteSuite(suite.id)
    suites.value = suites.value.filter((item) => item.id !== suite.id)
    if (activeSuiteId.value === suite.id) {
      activeSuiteId.value = suites.value[0]?.id ?? null
      records.value = []
    }
    ElMessage.success('已删除')
  } catch {
    // 已提示
  }
}

async function runSuite(): Promise<void> {
  if (!activeSuiteId.value) return
  running.value = true
  resultError.value = null
  try {
    const result = await evalApi.run(activeSuiteId.value, {
      prompt_version_id: versionId.value,
      temperature: temperature.value,
    })
    await loadResults()
    ElMessage.success(
      result.avg_score === null
        ? '测试完成（没有填写评分要点，只记录了回答）'
        : `测试完成，平均分 ${result.avg_score}`,
    )
  } catch (err) {
    resultError.value = getApiErrorMessage(err, '测试没能完成，请稍后再试')
  } finally {
    running.value = false
  }
}

function goBack(): void {
  router.push(`/prompts/${promptId}`)
}

// 切换评测集后重新拉取该集的历史结果
watch(activeSuiteId, () => {
  resultError.value = null
  void loadResults()
})

onMounted(loadAll)
</script>

<style scoped>
.lab-page {
  display: flex;
  flex-direction: column;
  gap: var(--rh-space-lg);
}

.lab-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--rh-space-base);
}

.back {
  margin-bottom: 4px;
  padding-left: 0;
  color: var(--rh-text-tertiary);
}

.lab-head h1 {
  font-family: var(--rh-font-display);
  font-size: var(--rh-fs-2xl);
  font-weight: 500;
  line-height: var(--rh-lh-tight);
}

.sub {
  margin-top: 6px;
  color: var(--rh-text-secondary);
  font-size: var(--rh-fs-base);
}

.sub-meta {
  color: var(--rh-text-tertiary);
  font-size: var(--rh-fs-md);
}

.lab-body {
  display: grid;
  grid-template-columns: 232px 1fr;
  gap: var(--rh-space-lg);
  align-items: start;
}

.suite-rail {
  padding: var(--rh-space-base);
  border: 1px solid var(--rh-border);
  border-radius: var(--rh-radius-md);
  background: var(--rh-bg-card);
}

.rail-title {
  margin-bottom: 10px;
  color: var(--rh-text-tertiary);
  font-size: var(--rh-fs-xs);
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.suite-list {
  display: grid;
  gap: 4px;
  list-style: none;
}

.suite-list li {
  display: flex;
  align-items: center;
  gap: 2px;
}

.suite-item {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  min-width: 0;
  padding: 8px 10px;
  border: 1px solid transparent;
  border-radius: var(--rh-radius-xs);
  background: transparent;
  color: var(--rh-text-secondary);
  text-align: left;
  cursor: pointer;
  transition: var(--rh-transition-all-fast);
}

.suite-item:hover {
  background: var(--rh-bg-hover);
  color: var(--rh-text-primary);
}

.suite-item.active {
  border-color: var(--rh-ai-strong);
  background: var(--rh-bg-inset);
  color: var(--rh-text-primary);
}

.suite-name {
  overflow: hidden;
  max-width: 100%;
  font-size: var(--rh-fs-md);
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.suite-count {
  color: var(--rh-text-tertiary);
  font-size: var(--rh-fs-xs);
}

.suite-del {
  padding: 4px;
  color: var(--rh-text-tertiary);
}

.suite-del:hover {
  color: var(--rh-danger);
}

.lab-main {
  display: flex;
  flex-direction: column;
  gap: var(--rh-space-base);
  min-width: 0;
}

.suite-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--rh-space-base);
}

.suite-head h2 {
  font-size: var(--rh-fs-xl);
  font-weight: 600;
}

.suite-desc {
  margin-top: 4px;
  color: var(--rh-text-secondary);
  font-size: var(--rh-fs-md);
}

.suite-meta {
  margin-top: 4px;
  color: var(--rh-text-tertiary);
  font-size: var(--rh-fs-sm);
}

.run-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--rh-space-sm);
  padding: var(--rh-space-md);
  border: 1px solid var(--rh-border-faint);
  border-radius: var(--rh-radius-sm);
  background: var(--rh-bg-secondary);
}

.run-version {
  width: 220px;
}

.run-temp-label {
  color: var(--rh-text-secondary);
  font-size: var(--rh-fs-sm);
  font-weight: 600;
}

.run-temp-note {
  color: var(--rh-text-tertiary);
  font-weight: 400;
}

.run-hint {
  margin-top: calc(-1 * var(--rh-space-sm));
  color: var(--rh-text-tertiary);
  font-size: var(--rh-fs-sm);
}

.result-block {
  display: grid;
  gap: var(--rh-space-sm);
}

.result-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--rh-space-base);
  padding: var(--rh-space-md) var(--rh-space-base);
  border: 1px solid var(--rh-border);
  border-radius: var(--rh-radius-sm);
  background: var(--rh-bg-card);
}

.score-board {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.score-num {
  font-family: var(--rh-font-display);
  font-size: var(--rh-fs-2xl);
  font-weight: 600;
  line-height: 1;
  color: var(--rh-ai-strong);
}

.score-label {
  color: var(--rh-text-tertiary);
  font-size: var(--rh-fs-sm);
}

.result-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--rh-space-base);
  color: var(--rh-text-tertiary);
  font-size: var(--rh-fs-sm);
}

.case-card {
  display: grid;
  gap: 8px;
  padding: var(--rh-space-base);
  border: 1px solid var(--rh-border-faint);
  border-radius: var(--rh-radius-sm);
  background: var(--rh-bg-card);
}

.case-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.case-vars {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.case-no-var {
  color: var(--rh-text-tertiary);
  font-size: var(--rh-fs-sm);
}

.case-score {
  min-width: 48px;
  padding: 2px 8px;
  border-radius: var(--rh-radius-xs);
  font-family: var(--rh-font-mono);
  font-size: var(--rh-fs-md);
  font-weight: 700;
  text-align: center;
}

.case-score.is-good {
  background: var(--rh-success-subtle);
  color: var(--rh-success-strong);
}

.case-score.is-mid {
  background: var(--rh-warning-subtle);
  color: var(--rh-warning);
}

.case-score.is-bad {
  background: var(--rh-danger-subtle);
  color: var(--rh-danger);
}

.case-score.is-none {
  background: var(--rh-bg-inset);
  color: var(--rh-text-tertiary);
}

.case-reason {
  color: var(--rh-text-secondary);
  font-size: var(--rh-fs-md);
  line-height: var(--rh-lh-base);
}

.case-output summary {
  color: var(--rh-text-tertiary);
  font-size: var(--rh-fs-sm);
  cursor: pointer;
}

.case-output pre {
  max-height: 220px;
  margin-top: 8px;
  padding: 10px 12px;
  overflow: auto;
  border-radius: var(--rh-radius-xs);
  background: var(--rh-bg-inset);
  color: var(--rh-text-secondary);
  font-family: var(--rh-font-mono);
  font-size: var(--rh-fs-sm);
  line-height: var(--rh-lh-base);
  white-space: pre-wrap;
  word-break: break-word;
}

.history-block h3 {
  margin-bottom: 8px;
  font-size: var(--rh-fs-base);
  font-weight: 600;
}

.history-list {
  display: grid;
  gap: 4px;
  list-style: none;
}

.history-item {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--rh-space-base);
  padding: 8px 12px;
  border: 1px solid var(--rh-border-faint);
  border-radius: var(--rh-radius-xs);
  color: var(--rh-text-tertiary);
  font-size: var(--rh-fs-sm);
}

.history-score {
  margin-left: auto;
  font-family: var(--rh-font-mono);
  font-weight: 700;
}

.history-score.is-good {
  color: var(--rh-success-strong);
}

.history-score.is-mid {
  color: var(--rh-warning);
}

.history-score.is-bad {
  color: var(--rh-danger);
}

.history-score.is-none {
  color: var(--rh-text-tertiary);
}

.case-editor {
  display: grid;
  gap: 10px;
  width: 100%;
}

.case-editor__item {
  display: grid;
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid var(--rh-border-faint);
  border-radius: var(--rh-radius-xs);
  background: var(--rh-bg-secondary);
}

.case-editor__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: var(--rh-fs-md);
}

.var-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 8px;
}

.var-field {
  display: grid;
  gap: 4px;
  font-size: var(--rh-fs-sm);
  color: var(--rh-text-secondary);
}

.no-var-hint,
.case-limit {
  color: var(--rh-text-tertiary);
  font-size: var(--rh-fs-xs);
}

@media (max-width: 900px) {
  .lab-body {
    grid-template-columns: 1fr;
  }

  .run-version {
    width: 100%;
  }
}
</style>

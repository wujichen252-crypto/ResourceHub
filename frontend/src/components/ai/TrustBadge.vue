<template>
  <!-- 可信度徽章：hover/聚焦弹出因子明细；rag 模式以外的模式只给解释文案 -->
  <el-popover
    placement="bottom-end"
    :width="260"
    trigger="hover"
    popper-class="trust-badge-popover"
  >
    <template #reference>
      <button
        class="trust-badge"
        :class="`is-${toneClass}`"
        type="button"
        :aria-label="`回答可信度：${label}`"
      >
        <span class="trust-dot" aria-hidden="true"></span>
        <span class="trust-label">{{ label }}</span>
        <span v-if="trust?.score !== null && trust?.score !== undefined" class="trust-score">
          {{ trust.score }}
        </span>
      </button>
    </template>

    <div class="trust-detail">
      <p class="trust-detail-title">{{ label }}</p>
      <template v-if="trust?.factors">
        <div v-if="trust.retrieval_degraded" class="trust-note trust-note--warn">
          向量检索不可用，质量按中性值计
        </div>
        <dl class="trust-factors">
          <div class="trust-factor">
            <dt>依据覆盖度</dt>
            <dd>{{ percent(trust.factors.coverage) }}</dd>
          </div>
          <div class="trust-factor">
            <dt>检索质量</dt>
            <dd>{{ percent(trust.factors.quality) }}</dd>
          </div>
          <div class="trust-factor">
            <dt>引用有效性</dt>
            <dd>{{ percent(trust.factors.validity) }}</dd>
          </div>
        </dl>
        <p class="trust-meta">
          {{ trust.cited_sentence_count }}/{{ trust.sentence_count }} 句带来源标注
        </p>
        <p v-if="trust.invalid_indices.length" class="trust-note trust-note--warn">
          无效引用编号：{{ trust.invalid_indices.join('、') }}（回答引用了不存在的片段）
        </p>
      </template>
      <p v-else class="trust-note">{{ modeHint }}</p>
    </div>
  </el-popover>
</template>

<script setup lang="ts">
/**
 * 回答可信度徽章：展示等级与三因子明细（依据覆盖度 / 检索质量 / 引用有效性）。
 * 评分口径见 docs/回答可信度可视化与引用溯源高亮设计方案.md §2。
 */
import { computed } from 'vue'
import type { TrustLevel, TrustReport } from '../../api/ai'

const props = defineProps<{ trust: TrustReport | null }>()

/** 无报告（旧消息/流中断）时不渲染，由父组件控制 */
const visibleTrust = computed(() => props.trust)

const LEVEL_LABELS: Record<TrustLevel, string> = {
  high: '高可信',
  mid: '中可信',
  low: '低可信',
  none: '无笔记依据',
  neutral: '通用知识',
}

const label = computed(() => {
  const trust = visibleTrust.value
  if (!trust) return ''
  if (trust.mode === 'refusal') return '无笔记依据'
  if (trust.mode === 'memory') return '基于记忆'
  if (trust.mode === 'general') return '通用知识'
  return LEVEL_LABELS[trust.level] ?? '低可信'
})

/** 徽章配色档位：rag 按等级，其余模式用中性灰绿 */
const toneClass = computed(() => {
  const trust = visibleTrust.value
  if (!trust) return 'neutral'
  if (trust.mode === 'rag') return trust.level
  return 'neutral'
})

const modeHint = computed(() => {
  const trust = visibleTrust.value
  if (!trust) return ''
  if (trust.mode === 'refusal') return '你的笔记中没有找到能回答这个问题的内容，这条回答没有事实依据。'
  if (trust.mode === 'memory') return '这条回答基于 AI 记住的你的偏好与背景，未引用笔记原文。'
  return '这条回答来自模型通用知识，未引用你的笔记，请自行核实关键事实。'
})

function percent(value: number): string {
  return `${Math.round(value * 100)}%`
}
</script>

<style scoped>
.trust-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-left: auto;
  padding: 2px 9px;
  border: 1px solid var(--rh-border);
  border-radius: 999px;
  background: var(--rh-bg-card);
  color: var(--rh-text-secondary);
  font-size: var(--rh-fs-sm);
  font-weight: 700;
  cursor: default;
  transition: var(--rh-transition-all-fast);
}

.trust-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--rh-trust-high);
}

.trust-badge.is-high { color: var(--rh-trust-high); border-color: var(--rh-trust-high); background: var(--rh-trust-high-subtle); }
.trust-badge.is-high .trust-dot { background: var(--rh-trust-high); }
.trust-badge.is-mid { color: var(--rh-trust-mid); border-color: var(--rh-trust-mid); background: var(--rh-trust-mid-subtle); }
.trust-badge.is-mid .trust-dot { background: var(--rh-trust-mid); }
.trust-badge.is-low { color: var(--rh-trust-low); border-color: var(--rh-trust-low); background: var(--rh-trust-low-subtle); }
.trust-badge.is-low .trust-dot { background: var(--rh-trust-low); }
.trust-badge.is-neutral { color: var(--rh-info); border-color: var(--rh-border); }
.trust-badge.is-neutral .trust-dot { background: var(--rh-info); }

.trust-score {
  padding: 0 5px;
  border-radius: var(--rh-radius-xs);
  background: var(--rh-bg-inset);
  color: var(--rh-text-secondary);
  font-family: var(--rh-font-mono);
  font-size: var(--rh-fs-xs);
}

.trust-detail-title {
  margin: 0 0 8px;
  color: var(--rh-text-primary);
  font-size: var(--rh-fs-base);
  font-weight: 700;
}

.trust-factors {
  display: grid;
  gap: 6px;
  margin: 8px 0;
}

.trust-factor {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.trust-factor dt {
  color: var(--rh-text-secondary);
  font-size: var(--rh-fs-md);
}

.trust-factor dd {
  margin: 0;
  color: var(--rh-text-primary);
  font-family: var(--rh-font-mono);
  font-size: var(--rh-fs-md);
  font-weight: 700;
}

.trust-meta {
  margin: 0 0 6px;
  color: var(--rh-text-tertiary);
  font-size: var(--rh-fs-sm);
}

.trust-note {
  margin: 0;
  color: var(--rh-text-tertiary);
  font-size: var(--rh-fs-sm);
  line-height: var(--rh-lh-base);
}

.trust-note--warn {
  color: var(--rh-warning);
}
</style>

<template>
  <Teleport to="body">
    <Transition name="gs-fade">
      <div v-if="searchOpen" class="gs-overlay" @mousedown.self="closeSearch">
        <div class="gs-panel" role="dialog" aria-modal="true" aria-label="全局搜索">
          <div class="gs-input-row">
            <el-icon class="gs-search-icon"><Search /></el-icon>
            <input
              ref="inputRef"
              v-model="keyword"
              class="gs-input"
              type="text"
              placeholder="搜索笔记与提示词，或输入操作名直达…"
              aria-label="全局搜索关键词"
              @keydown="handleInputKeydown"
            />
            <span class="gs-esc-hint">Esc</span>
          </div>

          <div v-if="errorMessage" class="gs-error" role="alert">{{ errorMessage }}</div>

          <div ref="listRef" class="gs-results" role="listbox" aria-label="搜索结果">
            <template v-for="group in groups" :key="group.label">
              <div class="gs-group-label">{{ group.label }}</div>
              <button
                v-for="entry in group.entries"
                :key="entry.key"
                :ref="(el) => setEntryRef(entry.key, el)"
                class="gs-item"
                role="option"
                :class="{ active: entry.key === activeKey }"
                :aria-selected="entry.key === activeKey"
                :aria-label="entry.title"
                @mouseenter="activeKey = entry.key"
                @click="choose(entry)"
              >
                <span class="gs-item-icon" :class="entry.kind"><el-icon><component :is="entry.icon" /></el-icon></span>
                <span class="gs-item-body">
                  <span class="gs-item-title">
                    <template v-for="(seg, i) in highlight(entry.title)" :key="i">
                      <mark v-if="seg.hit" class="gs-hl">{{ seg.text }}</mark>
                      <template v-else>{{ seg.text }}</template>
                    </template>
                  </span>
                  <span v-if="entry.snippet" class="gs-item-snippet">
                    <template v-for="(seg, i) in highlight(entry.snippet)" :key="i">
                      <mark v-if="seg.hit" class="gs-hl">{{ seg.text }}</mark>
                      <template v-else>{{ seg.text }}</template>
                    </template>
                  </span>
                  <span v-if="entry.meta" class="gs-item-meta">{{ entry.meta }}</span>
                </span>
                <el-icon v-if="entry.key === activeKey" class="gs-enter-hint"><BottomRight /></el-icon>
              </button>
            </template>

            <div v-if="flatEntries.length === 0 && keyword.trim()" class="gs-empty">
              未找到与 “{{ keyword.trim() }}” 相关的内容
            </div>
          </div>

          <div class="gs-footer">
            <span><kbd>↑</kbd><kbd>↓</kbd> 选择</span>
            <span><kbd>↵</kbd> 跳转</span>
            <span><kbd>Esc</kbd> 关闭</span>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Collection, Document, Cpu, DataAnalysis, Grid, MagicStick, Monitor, Search, Setting, BottomRight } from '@element-plus/icons-vue'
import { searchApi, type SearchResultItem } from '../../api/search'
import { useGlobalSearch } from '../../composables/useGlobalSearch'
import { getApiErrorMessage } from '../../api/http'
import { formatRelative } from '../../utils/format'

const router = useRouter()
const { searchOpen, closeSearch } = useGlobalSearch()

const keyword = ref('')
const inputRef = ref<HTMLInputElement | null>(null)
const listRef = ref<HTMLElement | null>(null)
const loading = ref(false)
const errorMessage = ref('')
const remoteItems = ref<SearchResultItem[]>([])
const activeKey = ref('')
const entryRefs = new Map<string, HTMLElement>()

// ── 快捷操作（前端静态数据，按输入过滤，兜底直达功能页） ──
interface ActionEntry { label: string; path: string; icon: unknown }
const actions: ActionEntry[] = [
  { label: '新建提示词', path: '/prompts/new', icon: MagicStick },
  { label: '打开 AI 工作台', path: '/ai', icon: Cpu },
  { label: '打开笔记库', path: '/notes', icon: Document },
  { label: '打开提示词库', path: '/prompts', icon: Collection },
  { label: '打开 ROI 看板', path: '/roi', icon: DataAnalysis },
  { label: '打开资源广场', path: '/plaza', icon: Grid },
  { label: '打开工作台', path: '/dashboard', icon: Monitor },
  { label: '打开设置', path: '/settings', icon: Setting },
]

interface Entry {
  key: string
  kind: 'note' | 'prompt' | 'action'
  title: string
  snippet?: string
  meta?: string
  icon: unknown
  path: string
}

const filteredActions = computed<Entry[]>(() => {
  const q = keyword.value.trim().toLowerCase()
  return actions
    .filter((a) => !q || a.label.toLowerCase().includes(q))
    .map((a, i) => ({
      key: `action-${i}`,
      kind: 'action' as const,
      title: a.label,
      icon: a.icon,
      path: a.path,
    }))
})

const remoteEntries = computed<Entry[]>(() =>
  remoteItems.value.map((item) => ({
    key: `${item.type}-${item.id}`,
    kind: item.type,
    title: item.title,
    snippet: item.snippet || undefined,
    meta: [
      item.category_name,
      item.updated_at ? formatRelative(item.updated_at) : '',
    ].filter(Boolean).join(' · ') || undefined,
    icon: item.type === 'note' ? Document : MagicStick,
    path: item.type === 'note' ? '/notes' : `/prompts/${item.id}`,
  })),
)

interface Group { label: string; entries: Entry[] }
const groups = computed<Group[]>(() => {
  const remote = remoteEntries.value
  const acts = filteredActions.value
  const list: Group[] = []
  const notes = remote.filter((e) => e.kind === 'note')
  const prompts = remote.filter((e) => e.kind === 'prompt')
  if (notes.length) list.push({ label: '笔记', entries: notes })
  if (prompts.length) list.push({ label: '提示词', entries: prompts })
  if (acts.length) list.push({ label: '快捷操作', entries: acts })
  return list
})

const flatEntries = computed<Entry[]>(() => groups.value.flatMap((g) => g.entries))

// 关键词变化时高亮项重置为第一个
watch(flatEntries, (entries) => {
  if (!entries.some((e) => e.key === activeKey.value)) {
    activeKey.value = entries[0]?.key ?? ''
  }
})

function setEntryRef(key: string, el: unknown) {
  if (el) entryRefs.set(key, el as HTMLElement)
  else entryRefs.delete(key)
}

// ── 关键词高亮：大小写不敏感分段 ──
interface Seg { text: string; hit: boolean }
function highlight(text: string): Seg[] {
  const q = keyword.value.trim()
  if (!q) return [{ text, hit: false }]
  const lower = text.toLowerCase()
  const ql = q.toLowerCase()
  const segs: Seg[] = []
  let pos = 0
  while (pos < text.length) {
    const idx = lower.indexOf(ql, pos)
    if (idx === -1) {
      segs.push({ text: text.slice(pos), hit: false })
      break
    }
    if (idx > pos) segs.push({ text: text.slice(pos, idx), hit: false })
    segs.push({ text: text.slice(idx, idx + q.length), hit: true })
    pos = idx + q.length
  }
  return segs
}

// ── 防抖搜索 + 请求序号守卫（只采纳最后一次请求的结果） ──
let debounceTimer: number | undefined
let requestSeq = 0

watch(keyword, () => {
  window.clearTimeout(debounceTimer)
  errorMessage.value = ''
  const q = keyword.value.trim()
  if (!q) {
    remoteItems.value = []
    loading.value = false
    return
  }
  debounceTimer = window.setTimeout(async () => {
    const seq = ++requestSeq
    loading.value = true
    try {
      const res = await searchApi.search(q)
      if (seq !== requestSeq) return
      remoteItems.value = res.items
      errorMessage.value = ''
    } catch (error) {
      if (seq !== requestSeq) return
      // 静默保留上次结果，仅顶部浅色提示，不打断输入
      errorMessage.value = getApiErrorMessage(error, '搜索失败，请稍后再试')
    } finally {
      if (seq === requestSeq) loading.value = false
    }
  }, 250)
})

// ── 键盘交互 ──
function handleInputKeydown(event: KeyboardEvent) {
  if (event.isComposing) return // 中文输入法选词期间不响应
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    moveActive(1)
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    moveActive(-1)
  } else if (event.key === 'Enter') {
    event.preventDefault()
    const entry = flatEntries.value.find((e) => e.key === activeKey.value)
    if (entry) choose(entry)
  } else if (event.key === 'Escape') {
    event.preventDefault()
    closeSearch()
  }
}

function moveActive(delta: number) {
  const entries = flatEntries.value
  if (!entries.length) return
  const idx = entries.findIndex((e) => e.key === activeKey.value)
  const next = idx === -1 ? 0 : (idx + delta + entries.length) % entries.length
  activeKey.value = entries[next].key
  nextTick(() => entryRefs.get(activeKey.value)?.scrollIntoView({ block: 'nearest' }))
}

function choose(entry: Entry) {
  closeSearch()
  keyword.value = ''
  router.push(entry.path)
}

// ── 全局快捷键：Ctrl/Cmd + K 唤起/关闭 ──
function handleGlobalKeydown(event: KeyboardEvent) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    searchOpen.value = !searchOpen.value
  }
}

watch(searchOpen, async (open) => {
  if (open) {
    keyword.value = ''
    remoteItems.value = []
    errorMessage.value = ''
    activeKey.value = ''
    await nextTick()
    inputRef.value?.focus()
  }
})

onMounted(() => window.addEventListener('keydown', handleGlobalKeydown))
onUnmounted(() => {
  window.removeEventListener('keydown', handleGlobalKeydown)
  window.clearTimeout(debounceTimer)
})
</script>

<style scoped>
.gs-overlay {
  position: fixed;
  inset: 0;
  z-index: var(--rh-z-popover);
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 12vh 16px 16px;
  background: var(--rh-bg-overlay);
}

.gs-panel {
  display: flex;
  flex-direction: column;
  width: 560px;
  max-width: 100%;
  max-height: 62vh;
  border: 1px solid var(--rh-border);
  border-radius: var(--rh-radius-md);
  background: var(--rh-bg-elevated);
  box-shadow: var(--rh-shadow-lg);
  overflow: hidden;
}

.gs-input-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--rh-border-faint);
}

.gs-search-icon { color: var(--rh-text-tertiary); font-size: 17px; }

.gs-input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: none;
  background: transparent;
  color: var(--rh-text-primary);
  font-size: 15px;
}

.gs-input::placeholder { color: var(--rh-text-placeholder); }

.gs-esc-hint {
  flex: 0 0 auto;
  padding: 2px 7px;
  border: 1px solid var(--rh-border);
  border-radius: var(--rh-radius-xs);
  color: var(--rh-text-tertiary);
  font-size: 11px;
}

.gs-error {
  padding: 8px 16px;
  background: var(--rh-primary-subtle);
  color: var(--rh-primary);
  font-size: 12px;
}

.gs-results {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 8px;
}

.gs-group-label {
  padding: 10px 10px 6px;
  color: var(--rh-text-tertiary);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .04em;
}

.gs-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  width: 100%;
  padding: 9px 10px;
  border: 0;
  border-radius: var(--rh-radius-sm);
  background: transparent;
  color: var(--rh-text-secondary);
  text-align: left;
  cursor: pointer;
  transition: var(--rh-transition-all-normal);
}

.gs-item.active { background: var(--rh-bg-active); color: var(--rh-text-primary); }

.gs-item-icon {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  width: 30px;
  height: 30px;
  border-radius: var(--rh-radius-sm);
  background: var(--rh-bg-inset);
  color: var(--rh-text-secondary);
  font-size: 15px;
}

.gs-item-icon.note { background: var(--rh-primary-subtle); color: var(--rh-primary); }
.gs-item-icon.prompt { background: var(--rh-bg-active); color: var(--rh-ai-strong, var(--rh-primary)); }

.gs-item-body { flex: 1; min-width: 0; display: grid; gap: 2px; }

.gs-item-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--rh-text-primary);
  font-size: 14px;
  font-weight: 600;
}

.gs-item-snippet {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--rh-text-tertiary);
  font-size: 12px;
}

.gs-item-meta { color: var(--rh-text-tertiary); font-size: 11px; }

.gs-enter-hint { flex: 0 0 auto; margin-top: 7px; color: var(--rh-primary); font-size: 14px; }

.gs-hl {
  padding: 0 1px;
  background: var(--rh-primary-subtle);
  color: var(--rh-primary);
  border-radius: 2px;
}

.gs-empty {
  padding: 32px 16px;
  color: var(--rh-text-tertiary);
  font-size: 13px;
  text-align: center;
}

.gs-footer {
  display: flex;
  gap: 16px;
  padding: 9px 16px;
  border-top: 1px solid var(--rh-border-faint);
  color: var(--rh-text-tertiary);
  font-size: 11px;
}

.gs-footer kbd {
  display: inline-block;
  min-width: 16px;
  margin-right: 3px;
  padding: 1px 5px;
  border: 1px solid var(--rh-border);
  border-radius: var(--rh-radius-xs);
  text-align: center;
  font-family: inherit;
  font-size: 10px;
}

.gs-fade-enter-active, .gs-fade-leave-active { transition: opacity .15s ease; }
.gs-fade-enter-from, .gs-fade-leave-to { opacity: 0; }

@media (max-width: 768px) {
  .gs-overlay { padding-top: 8vh; }
}
</style>

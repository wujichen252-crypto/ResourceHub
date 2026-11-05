<!--
SlashMenu.vue — @tiptap/suggestion 触发的块类型菜单
- 由 slashCommand.ts 通过 VueRenderer 实例化，props.items / props.command / props.decorationNode 注入
- 键盘 ↑↓ 切换、Enter 执行、Esc 关闭；无 tippy 依赖
- 定位由装饰节点（@tiptap/suggestion 的 decoration）负责，本组件只需 fixed 定位
-->
<template>
  <div
    v-if="visible"
    ref="menuRef"
    class="slash-menu"
    :style="menuStyle"
    role="menu"
    aria-label="块类型"
  >
    <div class="slash-menu__header">选择块类型（输入关键词可筛选）</div>
    <div class="slash-menu__list">
      <button
        v-for="(item, idx) in filteredItems"
        :key="item.title"
        type="button"
        class="slash-item"
        :class="{ 'is-active': idx === activeIndex }"
        role="menuitem"
        :aria-selected="idx === activeIndex"
        @mousedown.prevent="pickItem(idx)"
        @mouseenter="activeIndex = idx"
      >
        <span class="slash-item__icon">{{ item.icon }}</span>
        <span class="slash-item__text">
          <span class="slash-item__title">{{ item.title }}</span>
          <span class="slash-item__desc">{{ item.description }}</span>
        </span>
        <kbd v-if="item.shortcut" class="slash-item__kbd">{{ item.shortcut }}</kbd>
      </button>
      <div v-if="filteredItems.length === 0" class="slash-empty">没有匹配的块类型</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

export interface SlashMenuItem {
  title: string
  description: string
  icon: string
  shortcut?: string
  keywords?: string
  command: (payload: { editor: any; range: any }) => void
}

const props = defineProps<{
  items: SlashMenuItem[]
  query?: string
  // 装饰节点提供定位坐标（from @tiptap/suggestion decoration）
  position?: { top: number; left: number } | null
}>()

const emit = defineEmits<{
  (e: 'select', item: SlashMenuItem): void
  (e: 'close'): void
}>()

const visible = ref(true)
const activeIndex = ref(0)
const menuRef = ref<HTMLElement | null>(null)

const filteredItems = computed(() => {
  if (!props.query) return props.items
  const q = props.query.toLowerCase()
  return props.items.filter((i) => {
    if (i.title.toLowerCase().includes(q)) return true
    if (i.keywords?.toLowerCase().includes(q)) return true
    return false
  })
})

const menuStyle = computed(() => {
  if (!props.position) return {}
  return {
    position: 'fixed' as const,
    top: `${props.position.top}px`,
    left: `${props.position.left}px`,
  }
})

watch(
  () => props.query,
  () => {
    activeIndex.value = 0
  },
)

function pickItem(idx: number) {
  const item = filteredItems.value[idx]
  if (!item) return
  emit('select', item)
}

function onKeyDown(e: KeyboardEvent) {
  if (!filteredItems.value.length) {
    if (e.key === 'Escape') close()
    return
  }
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    activeIndex.value = (activeIndex.value + 1) % filteredItems.value.length
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    activeIndex.value =
      (activeIndex.value - 1 + filteredItems.value.length) % filteredItems.value.length
  } else if (e.key === 'Enter') {
    e.preventDefault()
    pickItem(activeIndex.value)
  } else if (e.key === 'Escape') {
    e.preventDefault()
    close()
  }
}

function close() {
  visible.value = false
  emit('close')
}

onMounted(() => {
  document.addEventListener('keydown', onKeyDown, true)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeyDown, true)
})
</script>

<style scoped>
.slash-menu {
  z-index: var(--rh-z-popover);
  background: var(--rh-bg-card);
  border: 1px solid var(--rh-border);
  border-radius: var(--rh-radius-sm);
  box-shadow: var(--rh-shadow-lg);
  min-width: 260px;
  max-height: 380px;
  overflow-y: auto;
  font-size: 13px;
}

.slash-menu__header {
  padding: 8px 12px;
  font-size: 12px;
  color: var(--rh-text-tertiary);
  border-bottom: 1px solid var(--rh-border-faint);
}

.slash-menu__list {
  padding: 4px;
}

.slash-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 10px;
  border: none;
  border-radius: var(--rh-radius-xs);
  background: transparent;
  color: var(--rh-text-primary);
  cursor: pointer;
  text-align: left;
  font: inherit;
}

.slash-item:hover,
.slash-item.is-active {
  background: var(--rh-bg-hover);
}

.slash-item__icon {
  flex-shrink: 0;
  width: 22px;
  text-align: center;
  font-family: var(--rh-font-sans);
  font-weight: 600;
  color: var(--rh-primary);
}

.slash-item__text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.slash-item__title {
  font-weight: 600;
  color: var(--rh-text-primary);
}

.slash-item__desc {
  font-size: 11px;
  color: var(--rh-text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.slash-item__kbd {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 10px;
  color: var(--rh-text-tertiary);
  padding: 1px 4px;
  border: 1px solid var(--rh-border-faint);
  border-radius: 3px;
  background: var(--rh-bg-subtle);
}

.slash-empty {
  padding: 12px;
  text-align: center;
  color: var(--rh-text-tertiary);
  font-size: 12px;
}
</style>

<template>
  <teleport to="body">
    <div
      v-if="visible"
      ref="menuRef"
      class="inline-ai-menu"
      role="menu"
      aria-label="内联 AI 操作菜单"
      :style="menuStyle"
      @mousedown.stop
    >
      <div class="menu-actions">
        <button
          type="button"
          class="menu-btn"
          role="menuitem"
          :disabled="!aiConfigured"
          :aria-label="aiConfigured ? '解释选中文本' : 'AI 未配置'"
          @click="handleAction('explain')"
        >解释</button>
        <button
          type="button"
          class="menu-btn"
          role="menuitem"
          :class="{ 'is-active': expanded === 'rewrite' }"
          :disabled="!aiConfigured"
          aria-label="改写选中文本"
          @click="handleAction('rewrite')"
        >改写</button>
        <button
          type="button"
          class="menu-btn"
          role="menuitem"
          :class="{ 'is-active': expanded === 'ask' }"
          :disabled="!aiConfigured"
          aria-label="基于选中文本提问"
          @click="handleAction('ask')"
        >提问</button>
        <button
          type="button"
          class="menu-close"
          aria-label="关闭内联 AI 菜单"
          @click="emit('close')"
        >×</button>
      </div>

      <!-- 改写附加要求 / 提问问题：点按钮后展开输入行 -->
      <div v-if="expanded" class="menu-input-row">
        <input
          ref="inputRef"
          v-model="inputText"
          class="menu-input"
          type="text"
          :placeholder="expanded === 'rewrite' ? '改写附加要求，如：更口语化（可选）' : '输入你的问题（必填）'"
          :aria-label="expanded === 'rewrite' ? '改写附加要求' : '问题内容'"
          maxlength="500"
          @keydown.enter.prevent="confirmExpanded"
          @keydown.esc.stop="emit('close')"
        />
        <button
          type="button"
          class="menu-btn is-confirm"
          :disabled="expanded === 'ask' && !inputText.trim()"
          aria-label="确认发送"
          @click="confirmExpanded"
        >确定</button>
      </div>

      <p v-if="!aiConfigured" class="menu-tip">AI 未配置，请到设置中填写 API Key</p>
    </div>
  </teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onUnmounted } from 'vue'
import type { InlineActionName } from '../../api/ai'

const props = defineProps<{
  visible: boolean
  aiConfigured: boolean
  rect: { top: number; left: number; bottom: number }
}>()

const emit = defineEmits<{
  action: [name: InlineActionName, instruction: string]
  close: []
}>()

const menuRef = ref<HTMLElement>()
const inputRef = ref<HTMLInputElement>()
/** 展开的输入行：改写（附加要求可选）或提问（问题必填） */
const expanded = ref<'rewrite' | 'ask' | null>(null)
const inputText = ref('')

// 菜单尺寸估算，用于定位翻转与视口防越界
const MENU_WIDTH = 280
const MENU_HEIGHT = 46

const menuStyle = computed(() => {
  const top = props.rect.top - MENU_HEIGHT - 8
  const flip = top < 8 // 上方空间不足时翻转到选区下方
  return {
    left: `${Math.min(Math.max(8, props.rect.left), window.innerWidth - MENU_WIDTH - 8)}px`,
    top: `${flip ? props.rect.bottom + 8 : top}px`,
  }
})

// 每次弹出复位展开态，避免上一次的输入残留
watch(() => props.visible, (val) => {
  if (val) {
    expanded.value = null
    inputText.value = ''
  }
})

function handleAction(name: InlineActionName) {
  if (name === 'explain') {
    emit('action', 'explain', '')
    return
  }
  if (expanded.value === name) return
  expanded.value = name
  inputText.value = ''
  nextTick(() => inputRef.value?.focus())
}

function confirmExpanded() {
  const text = inputText.value.trim()
  if (expanded.value === 'ask' && !text) return // 提问必须有内容
  emit('action', expanded.value as InlineActionName, text)
}

// 点击菜单外部关闭；Esc 关闭
function handleOutside(e: MouseEvent) {
  if (props.visible && menuRef.value && !menuRef.value.contains(e.target as Node)) {
    emit('close')
  }
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && props.visible) emit('close')
}

document.addEventListener('mousedown', handleOutside)
document.addEventListener('keydown', handleKeydown)

onUnmounted(() => {
  document.removeEventListener('mousedown', handleOutside)
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.inline-ai-menu {
  position: fixed;
  z-index: var(--rh-z-popover);
  background: var(--rh-bg-card);
  border: 1px solid var(--rh-ai-strong);
  border-radius: var(--rh-radius-sm);
  box-shadow: var(--rh-shadow-lg);
  padding: 6px;
  max-width: 320px;
}

.menu-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.menu-btn {
  border: none;
  background: transparent;
  color: var(--rh-ai-strong);
  font-size: 13px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: var(--rh-radius-xs);
  cursor: pointer;
  transition: background-color var(--rh-duration-fast) var(--rh-transition-fast);
}

.menu-btn:hover:not(:disabled),
.menu-btn.is-active {
  background: var(--rh-ai);
  color: var(--rh-on-ai);
}

.menu-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.menu-btn.is-confirm {
  background: var(--rh-ai);
  color: var(--rh-on-ai);
}

.menu-btn.is-confirm:disabled {
  opacity: 0.45;
}

.menu-close {
  margin-left: auto;
  border: none;
  background: transparent;
  color: var(--rh-text-tertiary);
  font-size: 15px;
  line-height: 1;
  padding: 2px 6px;
  cursor: pointer;
  border-radius: var(--rh-radius-xs);
}

.menu-close:hover {
  background: var(--rh-bg-hover);
  color: var(--rh-text-primary);
}

.menu-input-row {
  display: flex;
  gap: 4px;
  margin-top: 6px;
}

.menu-input {
  flex: 1;
  min-width: 0;
  border: 1px solid var(--rh-border);
  border-radius: var(--rh-radius-xs);
  background: var(--rh-bg-base);
  color: var(--rh-text-primary);
  font-size: 12px;
  padding: 4px 8px;
}

.menu-input:focus-visible {
  outline: none;
  border-color: var(--rh-ai-strong);
}

.menu-tip {
  margin: 6px 2px 0;
  font-size: 12px;
  color: var(--rh-text-tertiary);
}
</style>

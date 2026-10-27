/**
 * 全站主题状态（模块级单例，供导航栏 / 设置页共享）
 * - 偏好支持 浅色 / 深色 / 跟随系统 三种
 * - 统一通过 html[data-theme] 驱动 CSS 变量与图表重渲染
 * - 与 index.html 的内联脚本共用同一套解析规则，避免首屏闪色
 */
import { computed, ref } from 'vue'

export type ThemePreference = 'light' | 'dark' | 'system'

const STORAGE_KEY = 'theme'
const media = typeof window !== 'undefined' ? window.matchMedia?.('(prefers-color-scheme: dark)') : undefined

/** 读取已保存偏好；从未保存过视为跟随系统 */
function readPreference(): ThemePreference {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored === 'light' || stored === 'dark' ? stored : 'system'
  } catch {
    return 'system'
  }
}

/** 把偏好解析为实际生效的主题 */
function resolveTheme(pref: ThemePreference): 'light' | 'dark' {
  if (pref === 'system') return media?.matches ? 'dark' : 'light'
  return pref
}

function applyTheme(pref: ThemePreference): 'light' | 'dark' {
  const next = resolveTheme(pref)
  document.documentElement.setAttribute('data-theme', next)
  // Element Plus 官方深色变量挂载在 html.dark 上，必须与 data-theme 同步切换
  document.documentElement.classList.toggle('dark', next === 'dark')
  return next
}

const preference = ref<ThemePreference>(readPreference())
const resolvedTheme = ref<'light' | 'dark'>(applyTheme(preference.value))

export function useTheme() {
  const isDark = computed(() => resolvedTheme.value === 'dark')
  const themeLabel = computed(() => (isDark.value ? '切换至浅色模式' : '切换至深色模式'))

  /** 在浅色 / 深色之间切换（以当前实际生效的主题为基准） */
  function toggleTheme() {
    setPreference(resolvedTheme.value === 'dark' ? 'light' : 'dark')
  }

  /** 显式设置偏好（保留"跟随系统"选项） */
  function setPreference(pref: ThemePreference) {
    preference.value = pref
    try {
      if (pref === 'system') localStorage.removeItem(STORAGE_KEY)
      else localStorage.setItem(STORAGE_KEY, pref)
    } catch {
      /* localStorage 不可用时仅在内存中生效 */
    }
    resolvedTheme.value = applyTheme(pref)
  }

  return { preference, resolvedTheme, isDark, themeLabel, toggleTheme, setPreference }
}

// 偏好为「跟随系统」时，实时响应系统外观变化
media?.addEventListener('change', () => {
  if (preference.value === 'system') resolvedTheme.value = applyTheme('system')
})

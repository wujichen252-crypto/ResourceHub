import { ref } from 'vue'

/**
 * 全局命令面板（Ctrl/Cmd + K）开关的单例状态。
 * 模块级 ref 与 useTheme 同一模式：NavBar 的搜索按钮与 GlobalSearch
 * 组件共享同一份状态，无需事件总线或 Pinia。
 */
const searchOpen = ref(false)

function openSearch() {
  searchOpen.value = true
}

function closeSearch() {
  searchOpen.value = false
}

function toggleSearch() {
  searchOpen.value = !searchOpen.value
}

export function useGlobalSearch() {
  return { searchOpen, openSearch, closeSearch, toggleSearch }
}

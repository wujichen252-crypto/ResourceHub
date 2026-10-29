<template>
  <aside class="workspace-nav">
    <RouterLink class="brand" to="/dashboard">
      <span class="brand-mark">R</span>
      <div><strong>ResourceHub</strong><small>个人资源工作台</small></div>
    </RouterLink>

    <button class="quick-create" @click="router.push('/prompts/new')">
      <el-icon><Plus /></el-icon><span>新建提示词</span>
    </button>

    <div class="nav-label">工作区</div>
    <nav class="nav-links">
      <RouterLink v-for="item in mainLinks" :key="item.path" class="nav-link" :to="item.path" :class="{ active: activeIndex === item.path }" :aria-current="activeIndex === item.path ? 'page' : undefined">
        <el-icon><component :is="item.icon" /></el-icon><span>{{ item.label }}</span>
        <span v-if="item.path === '/prompts'" class="nav-accent">AI</span>
        <span v-if="item.path === '/ai' && identityStore.unreadCount > 0" class="nav-badge">{{ identityStore.unreadCount > 9 ? '9+' : identityStore.unreadCount }}</span>
      </RouterLink>
    </nav>

    <div class="nav-label nav-label-lower">收藏与分类</div>
    <nav class="nav-links">
      <RouterLink class="nav-link" to="/prompts" @click="openFavorites"><el-icon><Star /></el-icon><span>收藏提示词</span></RouterLink>
      <RouterLink class="nav-link" to="/notes" :class="{ active: activeIndex === '/notes' }" :aria-current="activeIndex === '/notes' ? 'page' : undefined"><el-icon><Collection /></el-icon><span>我的笔记</span></RouterLink>
    </nav>

    <div ref="footerRef" class="nav-footer">
      <button class="nav-link" :class="{ active: activeIndex === '/settings' }" @click="router.push('/settings')"><el-icon><Setting /></el-icon><span>设置</span></button>
      <button class="nav-link" :aria-label="themeLabel" @click="toggleTheme"><el-icon><Moon v-if="isDark" /><Sunny v-else /></el-icon><span>{{ isDark ? '切换浅色模式' : '切换深色模式' }}</span></button>
      <div class="footer-rule"></div>
      <button class="user-trigger" :aria-label="`账户菜单，当前用户 ${authStore.user?.username || '用户'}`" :aria-expanded="userMenuOpen" @click="userMenuOpen = !userMenuOpen">
        <el-avatar :size="30" :src="authStore.user?.avatar || undefined">{{ avatarText }}</el-avatar>
        <span class="user-meta"><strong>{{ authStore.user?.username || '用户' }}</strong><small>已登录</small></span>
        <el-icon><ArrowDown /></el-icon>
      </button>
      <div v-if="userMenuOpen" class="user-popover" role="menu">
        <button role="menuitem" @click="router.push('/settings'); userMenuOpen = false"><el-icon><Setting /></el-icon>账户设置</button>
        <button role="menuitem" class="danger" @click="logout"><el-icon><SwitchButton /></el-icon>退出登录</button>
      </div>
    </div>
  </aside>

  <header class="mobile-topbar">
    <RouterLink class="mobile-brand" to="/dashboard"><span class="brand-mark">R</span><strong>ResourceHub</strong></RouterLink>
    <div class="mobile-actions">
      <button class="icon-button" :aria-label="themeLabel" @click="toggleTheme"><el-icon><Moon v-if="isDark" /><Sunny v-else /></el-icon></button>
      <button class="icon-button" :aria-label="mobileOpen ? '关闭菜单' : '打开菜单'" :aria-expanded="mobileOpen" @click="mobileOpen = !mobileOpen"><el-icon><Menu /></el-icon></button>
    </div>
  </header>
  <div v-if="mobileOpen" class="mobile-menu">
    <RouterLink v-for="item in mainLinks" :key="item.path" :to="item.path" @click="mobileOpen = false"><el-icon><component :is="item.icon" /></el-icon>{{ item.label }}<span v-if="item.path === '/ai' && identityStore.unreadCount > 0" class="nav-badge">{{ identityStore.unreadCount > 9 ? '9+' : identityStore.unreadCount }}</span></RouterLink>
    <RouterLink to="/prompts" @click="openFavorites(); mobileOpen = false"><el-icon><Star /></el-icon>收藏提示词</RouterLink>
    <RouterLink to="/notes" @click="mobileOpen = false"><el-icon><Collection /></el-icon>我的笔记</RouterLink>
    <RouterLink to="/settings" @click="mobileOpen = false"><el-icon><Setting /></el-icon>设置</RouterLink>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowDown, Collection, Cpu, Document, Grid, MagicStick, Menu, Monitor, Moon, Plus, Setting, Star, Sunny, SwitchButton } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import { usePromptsStore } from '../stores/prompts'
import { useAgentIdentityStore } from '../stores/agentIdentity'
import { useTheme } from '../composables/useTheme'

const router = useRouter(); const route = useRoute(); const authStore = useAuthStore(); const promptsStore = usePromptsStore(); const identityStore = useAgentIdentityStore()
const { isDark, themeLabel, toggleTheme } = useTheme()
const userMenuOpen = ref(false); const mobileOpen = ref(false); const footerRef = ref<HTMLElement | null>(null)
const mainLinks = [{ path: '/dashboard', label: '工作台', icon: Monitor }, { path: '/ai', label: 'AI 工作台', icon: Cpu }, { path: '/notes', label: '笔记库', icon: Document }, { path: '/prompts', label: '提示词库', icon: MagicStick }, { path: '/plaza', label: '资源广场', icon: Grid }]
const activeIndex = computed(() => route.path.startsWith('/ai') ? '/ai' : route.path.startsWith('/notes') ? '/notes' : route.path.startsWith('/prompts') ? '/prompts' : route.path.startsWith('/plaza') ? '/plaza' : route.path.startsWith('/settings') ? '/settings' : '/dashboard')
const avatarText = computed(() => (authStore.user?.username || '用户').charAt(0).toUpperCase())

/** 点击账户菜单外部或按 Esc 时收起弹层 */
function handleDocumentClick(event: MouseEvent) {
  if (userMenuOpen.value && !footerRef.value?.contains(event.target as Node)) userMenuOpen.value = false
}
function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') { userMenuOpen.value = false; mobileOpen.value = false }
}
onMounted(() => { document.addEventListener('click', handleDocumentClick); document.addEventListener('keydown', handleKeydown); void identityStore.loadStatus() })
onUnmounted(() => { document.removeEventListener('click', handleDocumentClick); document.removeEventListener('keydown', handleKeydown) })

function openFavorites() {
  promptsStore.showFavoritesOnly = true
  promptsStore.setPage(1)
}
function logout() { ElMessageBox.confirm('确定要退出登录吗？', '退出登录', { confirmButtonText: '退出', cancelButtonText: '取消', type: 'warning' }).then(() => { authStore.logout(); router.push('/login') }).catch(() => {}) }
</script>

<style scoped>
.workspace-nav { position: fixed; inset: 0 auto 0 0; z-index: var(--rh-z-nav); display: flex; flex-direction: column; width: var(--rh-nav-width); padding: 24px 14px 16px; background: var(--rh-bg-card); border-right: 1px solid var(--rh-border); }
.brand { display: flex; align-items: center; gap: 10px; padding: 0 10px 24px; text-decoration: none; color: var(--rh-text-primary); }
.brand-mark { display: grid; place-items: center; width: 32px; height: 32px; background: var(--rh-text-primary); color: var(--rh-bg-card); border-radius: 50%; font-family: Georgia, serif; font-size: 20px; font-weight: 700; }
.brand strong { display: block; font-family: Georgia, 'Times New Roman', serif; font-size: 18px; line-height: 1.05; letter-spacing: 0; }
.brand small { display: block; margin-top: 3px; color: var(--rh-text-tertiary); font-size: 11px; }
.quick-create { display: flex; align-items: center; gap: 8px; width: 100%; height: 40px; padding: 0 12px; border: 0; border-radius: var(--rh-radius-sm); background: var(--rh-primary); color: var(--rh-on-primary); font-weight: 600; cursor: pointer; transition: var(--rh-transition-all-normal); }
.quick-create:hover { background: var(--rh-primary-hover); transform: translateY(-1px); box-shadow: var(--rh-shadow-md); }
.nav-label { padding: 28px 12px 8px; color: var(--rh-text-tertiary); font-size: 11px; font-weight: 700; letter-spacing: .04em; }.nav-label-lower { padding-top: 24px; }
.nav-links { display: grid; gap: 3px; }
.nav-link { display: flex; align-items: center; gap: 10px; width: 100%; min-height: 38px; padding: 0 11px; border: 0; border-radius: var(--rh-radius-sm); background: transparent; color: var(--rh-text-secondary); text-align: left; text-decoration: none; cursor: pointer; transition: var(--rh-transition-all-normal); }
.nav-link:hover { background: var(--rh-bg-hover); color: var(--rh-text-primary); }.nav-link.active { background: var(--rh-bg-active); color: var(--rh-primary); font-weight: 700; }.nav-link :deep(.el-icon) { font-size: 17px; }.nav-accent { margin-left: auto; color: var(--rh-ai-strong); font-size: 10px; font-weight: 800; letter-spacing: .05em; }
.nav-badge { display: grid; place-items: center; min-width: 18px; height: 18px; margin-left: auto; padding: 0 5px; border-radius: 999px; background: var(--rh-primary); color: var(--rh-on-primary); font-size: 10px; font-weight: 800; line-height: 1; }
.nav-footer { position: relative; display: grid; gap: 3px; margin-top: auto; }.footer-rule { height: 1px; margin: 12px 10px; background: var(--rh-border-faint); }
.user-trigger { display: flex; align-items: center; gap: 9px; width: 100%; padding: 7px 9px; border: 0; border-radius: var(--rh-radius-sm); background: transparent; color: var(--rh-text-tertiary); text-align: left; cursor: pointer; }.user-trigger:hover { background: var(--rh-bg-hover); }.user-trigger :deep(.el-avatar) { flex: 0 0 auto; background: var(--rh-bg-active); color: var(--rh-text-secondary); font-weight: 700; }.user-meta { flex: 1; min-width: 0; }.user-meta strong, .user-meta small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.user-meta strong { color: var(--rh-text-primary); font-size: 13px; }.user-meta small { color: var(--rh-text-tertiary); font-size: 11px; }
.user-popover { position: absolute; right: 0; bottom: 52px; left: 0; padding: 5px; border: 1px solid var(--rh-border); border-radius: var(--rh-radius-md); background: var(--rh-bg-elevated); box-shadow: var(--rh-shadow-lg); }.user-popover button { display: flex; align-items: center; gap: 8px; width: 100%; padding: 9px 10px; border: 0; border-radius: var(--rh-radius-xs); background: transparent; color: var(--rh-text-secondary); text-align: left; cursor: pointer; }.user-popover button:hover { background: var(--rh-bg-hover); color: var(--rh-text-primary); }.user-popover button.danger:hover { color: var(--rh-danger); }
.mobile-topbar, .mobile-menu { display: none; }
@media (max-width: 768px) { .workspace-nav { display: none; }.mobile-topbar { position: fixed; inset: 0 0 auto; z-index: var(--rh-z-topbar); display: flex; align-items: center; justify-content: space-between; height: 60px; padding: 0 16px; border-bottom: 1px solid var(--rh-border); background: var(--rh-bg-card); }.mobile-brand { display: flex; align-items: center; gap: 8px; text-decoration: none; color: var(--rh-text-primary); }.mobile-brand .brand-mark { width: 28px; height: 28px; font-size: 17px; }.mobile-brand strong { font-family: Georgia, serif; font-size: 16px; }.mobile-actions { display: flex; gap: 4px; }.icon-button { display: grid; place-items: center; width: 36px; height: 36px; border: 0; border-radius: var(--rh-radius-sm); background: transparent; color: var(--rh-text-secondary); cursor: pointer; }.icon-button:hover { background: var(--rh-bg-hover); color: var(--rh-text-primary); }.mobile-menu { position: fixed; top: 60px; right: 0; left: 0; z-index: var(--rh-z-menu); display: grid; gap: 3px; padding: 10px 16px 14px; border-bottom: 1px solid var(--rh-border); background: var(--rh-bg-card); box-shadow: var(--rh-shadow-md); }.mobile-menu a { display: flex; align-items: center; gap: 10px; padding: 10px; border-radius: var(--rh-radius-sm); color: var(--rh-text-secondary); text-decoration: none; }.mobile-menu a:hover { background: var(--rh-bg-hover); color: var(--rh-text-primary); } }
</style>

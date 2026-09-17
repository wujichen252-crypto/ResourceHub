<template>
  <aside class="workspace-nav">
    <div class="brand" @click="router.push('/dashboard')">
      <span class="brand-mark">R</span>
      <div><strong>ResourceHub</strong><small>个人资源工作台</small></div>
    </div>

    <button class="quick-create" @click="router.push('/prompts/new')">
      <el-icon><Plus /></el-icon><span>新建提示词</span><kbd>N</kbd>
    </button>

    <div class="nav-label">工作区</div>
    <nav class="nav-links">
      <button v-for="item in mainLinks" :key="item.path" class="nav-link" :class="{ active: activeIndex === item.path }" @click="router.push(item.path)">
        <el-icon><component :is="item.icon" /></el-icon><span>{{ item.label }}</span>
        <span v-if="item.path === '/prompts'" class="nav-accent">AI</span>
      </button>
    </nav>

    <div class="nav-label nav-label-lower">收藏与分类</div>
    <nav class="nav-links">
      <button class="nav-link" @click="router.push('/prompts')"><el-icon><Star /></el-icon><span>收藏提示词</span></button>
      <button class="nav-link" @click="router.push('/notes')"><el-icon><Collection /></el-icon><span>全部资源</span></button>
    </nav>

    <div class="nav-footer">
      <button class="nav-link" :class="{ active: activeIndex === '/settings' }" @click="router.push('/settings')"><el-icon><Setting /></el-icon><span>设置</span></button>
      <div class="footer-rule"></div>
      <button class="user-trigger" @click="userMenuOpen = !userMenuOpen">
        <el-avatar :size="30" :src="authStore.user?.avatar || undefined">{{ avatarText }}</el-avatar>
        <span class="user-meta"><strong>{{ authStore.user?.username || '用户' }}</strong><small>已登录</small></span>
        <el-icon><ArrowDown /></el-icon>
      </button>
      <div v-if="userMenuOpen" class="user-popover">
        <button @click="router.push('/settings'); userMenuOpen = false"><el-icon><Setting /></el-icon>账户设置</button>
        <button class="danger" @click="logout"><el-icon><SwitchButton /></el-icon>退出登录</button>
      </div>
    </div>
  </aside>

  <header class="mobile-topbar">
    <button class="mobile-brand" @click="router.push('/dashboard')"><span class="brand-mark">R</span><strong>ResourceHub</strong></button>
    <div class="mobile-actions">
      <button class="icon-button" :aria-label="themeLabel" @click="toggleTheme"><el-icon><Moon v-if="isDark" /><Sunny v-else /></el-icon></button>
      <button class="icon-button" aria-label="打开菜单" @click="mobileOpen = !mobileOpen"><el-icon><Menu /></el-icon></button>
    </div>
  </header>
  <div v-if="mobileOpen" class="mobile-menu">
    <button v-for="item in mainLinks" :key="item.path" @click="router.push(item.path); mobileOpen = false"><el-icon><component :is="item.icon" /></el-icon>{{ item.label }}</button>
    <button @click="router.push('/settings'); mobileOpen = false"><el-icon><Setting /></el-icon>设置</button>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowDown, Collection, Document, MagicStick, Menu, Monitor, Moon, Plus, Setting, Star, Sunny, SwitchButton } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const router = useRouter(); const route = useRoute(); const authStore = useAuthStore()
const userMenuOpen = ref(false); const mobileOpen = ref(false)
const isDark = ref(document.documentElement.getAttribute('data-theme') === 'dark')
const mainLinks = [{ path: '/dashboard', label: '工作台', icon: Monitor }, { path: '/notes', label: '笔记库', icon: Document }, { path: '/prompts', label: '提示词库', icon: MagicStick }]
const activeIndex = computed(() => route.path.startsWith('/notes') ? '/notes' : route.path.startsWith('/prompts') ? '/prompts' : route.path.startsWith('/settings') ? '/settings' : '/dashboard')
const avatarText = computed(() => (authStore.user?.username || '用户').charAt(0).toUpperCase())
const themeLabel = computed(() => isDark.value ? '切换至浅色模式' : '切换至深色模式')

function toggleTheme() { const theme = isDark.value ? 'light' : 'dark'; document.documentElement.setAttribute('data-theme', theme); localStorage.setItem('theme', theme); isDark.value = !isDark.value }
function logout() { ElMessageBox.confirm('确定要退出登录吗？', '退出登录', { confirmButtonText: '退出', cancelButtonText: '取消', type: 'warning' }).then(() => { authStore.logout(); router.push('/login') }).catch(() => {}) }
</script>

<style scoped>
.workspace-nav { position: fixed; inset: 0 auto 0 0; z-index: 100; display: flex; flex-direction: column; width: var(--rh-nav-width); padding: 24px 14px 16px; background: var(--rh-bg-card); border-right: 1px solid var(--rh-border); }
.brand { display: flex; align-items: center; gap: 10px; padding: 0 10px 24px; cursor: pointer; color: var(--rh-text-primary); }
.brand-mark { display: grid; place-items: center; width: 32px; height: 32px; background: var(--rh-text-primary); color: var(--rh-bg-card); border-radius: 50%; font-family: Georgia, serif; font-size: 20px; font-weight: 700; }
.brand strong { display: block; font-family: Georgia, 'Times New Roman', serif; font-size: 18px; line-height: 1.05; letter-spacing: 0; }
.brand small { display: block; margin-top: 3px; color: var(--rh-text-tertiary); font-size: 11px; }
.quick-create { display: flex; align-items: center; gap: 8px; width: 100%; height: 40px; padding: 0 12px; border: 0; border-radius: var(--rh-radius-sm); background: var(--rh-primary); color: white; font-weight: 600; cursor: pointer; transition: var(--rh-transition-all-normal); }
.quick-create:hover { background: var(--rh-primary-hover); transform: translateY(-1px); box-shadow: var(--rh-shadow-md); }
.quick-create kbd { margin-left: auto; padding: 1px 5px; border: 1px solid rgba(255,255,255,.35); border-radius: 3px; font-size: 11px; opacity: .8; }
.nav-label { padding: 28px 12px 8px; color: var(--rh-text-tertiary); font-size: 10px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; }.nav-label-lower { padding-top: 24px; }
.nav-links { display: grid; gap: 3px; }
.nav-link { display: flex; align-items: center; gap: 10px; width: 100%; min-height: 38px; padding: 0 11px; border: 0; border-radius: var(--rh-radius-sm); background: transparent; color: var(--rh-text-secondary); text-align: left; cursor: pointer; transition: var(--rh-transition-all-normal); }
.nav-link:hover { background: var(--rh-bg-hover); color: var(--rh-text-primary); }.nav-link.active { background: var(--rh-bg-active); color: var(--rh-primary); font-weight: 700; }.nav-link :deep(.el-icon) { font-size: 17px; }.nav-accent { margin-left: auto; color: var(--rh-ai-strong); font-size: 10px; font-weight: 800; letter-spacing: .05em; }
.nav-footer { position: relative; margin-top: auto; }.footer-rule { height: 1px; margin: 12px 10px; background: var(--rh-border-faint); }
.user-trigger { display: flex; align-items: center; gap: 9px; width: 100%; padding: 7px 9px; border: 0; border-radius: var(--rh-radius-sm); background: transparent; color: var(--rh-text-tertiary); text-align: left; cursor: pointer; }.user-trigger:hover { background: var(--rh-bg-hover); }.user-trigger :deep(.el-avatar) { flex: 0 0 auto; background: var(--rh-ai); color: var(--rh-text-primary); font-weight: 800; }.user-meta { flex: 1; min-width: 0; }.user-meta strong, .user-meta small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.user-meta strong { color: var(--rh-text-primary); font-size: 13px; }.user-meta small { color: var(--rh-text-tertiary); font-size: 11px; }
.user-popover { position: absolute; right: 0; bottom: 52px; left: 0; padding: 5px; border: 1px solid var(--rh-border); border-radius: var(--rh-radius-md); background: var(--rh-bg-elevated); box-shadow: var(--rh-shadow-lg); }.user-popover button { display: flex; align-items: center; gap: 8px; width: 100%; padding: 9px 10px; border: 0; border-radius: var(--rh-radius-xs); background: transparent; color: var(--rh-text-secondary); text-align: left; cursor: pointer; }.user-popover button:hover { background: var(--rh-bg-hover); color: var(--rh-text-primary); }.user-popover button.danger:hover { color: var(--rh-danger); }
.mobile-topbar, .mobile-menu { display: none; }
@media (max-width: 768px) { .workspace-nav { display: none; }.mobile-topbar { position: fixed; inset: 0 0 auto; z-index: 110; display: flex; align-items: center; justify-content: space-between; height: 60px; padding: 0 16px; border-bottom: 1px solid var(--rh-border); background: var(--rh-bg-card); }.mobile-brand { display: flex; align-items: center; gap: 8px; border: 0; background: transparent; color: var(--rh-text-primary); cursor: pointer; }.mobile-brand .brand-mark { width: 28px; height: 28px; font-size: 17px; }.mobile-brand strong { font-family: Georgia, serif; font-size: 16px; }.mobile-actions { display: flex; gap: 4px; }.icon-button { display: grid; place-items: center; width: 36px; height: 36px; border: 0; border-radius: var(--rh-radius-sm); background: transparent; color: var(--rh-text-secondary); cursor: pointer; }.icon-button:hover { background: var(--rh-bg-hover); color: var(--rh-text-primary); }.mobile-menu { position: fixed; top: 60px; right: 0; left: 0; z-index: 109; display: grid; gap: 3px; padding: 10px 16px 14px; border-bottom: 1px solid var(--rh-border); background: var(--rh-bg-card); box-shadow: var(--rh-shadow-md); }.mobile-menu button { display: flex; align-items: center; gap: 10px; padding: 10px; border: 0; border-radius: var(--rh-radius-sm); background: transparent; color: var(--rh-text-secondary); text-align: left; }.mobile-menu button:hover { background: var(--rh-bg-hover); color: var(--rh-text-primary); } }
</style>

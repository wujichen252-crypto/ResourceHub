<template>
  <header class="navbar">
    <!-- Logo -->
    <div class="logo-item" @click="$router.push('/dashboard')">
      <span class="logo-icon">◆</span>
      <span class="logo-text">ResourceHub</span>
    </div>

    <!-- Navigation Menu -->
    <el-menu
      mode="horizontal"
      :ellipsis="false"
      :default-active="activeIndex"
      class="nav-menu"
      @select="handleSelect"
    >
      <el-menu-item index="/dashboard">
        <el-icon><Monitor /></el-icon>
        仪表盘
      </el-menu-item>
      <el-menu-item index="/notes">
        <el-icon><Document /></el-icon>
        笔记
      </el-menu-item>
      <el-menu-item index="/prompts">
        <el-icon><MagicStick /></el-icon>
        提示词库
      </el-menu-item>
    </el-menu>

    <!-- Right Section: Theme Toggle + User Menu -->
    <div class="navbar-right">
      <!-- Theme Toggle Button -->
      <el-tooltip :content="themeLabel" placement="bottom" :show-after="300">
        <el-button link class="theme-toggle" @click="toggleTheme">
          <el-icon v-if="isDark"><Moon /></el-icon>
          <el-icon v-else><Sunny /></el-icon>
        </el-button>
      </el-tooltip>

      <!-- User Dropdown -->
      <el-dropdown
        trigger="click"
        popper-class="user-menu-popper"
        @visible-change="onVisibleChange"
        @command="handleCommand"
      >
        <div class="user-trigger" :class="{ 'is-open': userMenuOpen }">
          <el-avatar :size="32" :src="authStore.user?.avatar || undefined" class="user-avatar">
            {{ avatarText }}
          </el-avatar>
          <span class="user-name">{{ authStore.user?.username || '用户' }}</span>
          <el-icon class="user-chevron"><ArrowDown /></el-icon>
        </div>
        <template #dropdown>
          <div class="user-card">
            <el-avatar :size="42" :src="authStore.user?.avatar || undefined" class="user-card-avatar">
              {{ avatarText }}
            </el-avatar>
            <div class="user-card-meta">
              <div class="user-card-name">{{ authStore.user?.username || '用户' }}</div>
              <div class="user-card-email">{{ authStore.user?.email || '未设置邮箱' }}</div>
            </div>
          </div>
          <el-dropdown-menu class="user-menu-list">
            <el-dropdown-item command="settings">
              <el-icon><Setting /></el-icon>
              <span>设置</span>
            </el-dropdown-item>
            <el-dropdown-item command="logout" divided class="user-menu-logout">
              <el-icon><SwitchButton /></el-icon>
              <span>退出登录</span>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  Monitor, Document, MagicStick, Setting, SwitchButton, ArrowDown,
  Moon, Sunny,
} from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const userMenuOpen = ref(false)

// ── Theme Toggle ──

const isDark = ref(document.documentElement.getAttribute('data-theme') === 'dark')

const themeLabel = computed(() => isDark.value ? '切换至浅色模式' : '切换至深色模式')

function toggleTheme() {
  const newTheme = isDark.value ? 'light' : 'dark'
  document.documentElement.setAttribute('data-theme', newTheme)
  localStorage.setItem('theme', newTheme)
  isDark.value = !isDark.value
}

// Listen for system preference changes
watch(isDark, () => {}) // trigger reactivity; initial sync done above

// ── Navigation State ──

const activeIndex = computed(() => {
  const path = route.path
  if (path.startsWith('/notes')) return '/notes'
  if (path.startsWith('/prompts')) return '/prompts'
  if (path.startsWith('/dashboard')) return '/dashboard'
  if (path.startsWith('/settings')) return '/settings'
  return ''
})

/** 头像占位：取用户名首字符 */
const avatarText = computed(() => {
  const name = authStore.user?.username || '用户'
  return name.charAt(0).toUpperCase()
})

function handleSelect(index: string) {
  if (index !== route.path) {
    router.push(index)
  }
}

function onVisibleChange(visible: boolean) {
  userMenuOpen.value = visible
}

function handleCommand(command: string) {
  if (command === 'settings') {
    router.push('/settings')
  } else if (command === 'logout') {
    ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }).then(() => {
      authStore.logout()
      router.push('/login')
    }).catch(() => {})
  }
}
</script>

<style scoped>
/* ── Top Bar Container ── */

.navbar {
  display: flex;
  align-items: center;
  padding: 0 20px;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--rh-border-faint);
  height: var(--rh-nav-height);
  position: sticky;
  top: 0;
  z-index: 100;
  transition: background-color var(--rh-duration-normal) var(--rh-transition-normal),
              border-color var(--rh-duration-normal) var(--rh-transition-normal);
}

[data-theme="dark"] .navbar {
  background: rgba(17, 24, 39, 0.8);
  border-bottom-color: var(--rh-border-faint);
}

/* ── Logo ── */

.logo-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 16px;
  color: var(--rh-text-primary);
  padding: 0 24px 0 0;
  white-space: nowrap;
  cursor: pointer;
  user-select: none;
  transition: opacity var(--rh-duration-fast) var(--rh-transition-fast);
}

.logo-item:hover {
  opacity: 0.8;
}

.logo-icon {
  color: var(--rh-primary);
  font-size: 14px;
  line-height: 1;
}

.logo-text {
  letter-spacing: -0.02em;
}

/* ── Navigation Menu ── */

.nav-menu {
  flex: 0 0 auto;
  height: 100%;
}

.nav-menu :deep(.el-menu-item) {
  font-size: 14px;
  font-weight: 500;
  color: var(--rh-text-secondary);
  border-bottom: none !important;
  transition: var(--rh-transition-all-normal);
  height: var(--rh-nav-height) !important;
  line-height: var(--rh-nav-height) !important;
}

.nav-menu :deep(.el-menu-item:hover) {
  color: var(--rh-primary) !important;
  background: transparent !important;
}

.nav-menu :deep(.el-menu-item.is-active) {
  color: var(--rh-primary) !important;
  border-bottom: none !important;
  position: relative;
}

.nav-menu :deep(.el-menu-item.is-active)::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%) scaleX(0.6);
  width: 20px;
  height: 2px;
  background: var(--rh-primary);
  border-radius: 1px;
  transition: transform var(--rh-duration-normal) var(--rh-transition-spring);
}

.nav-menu :deep(.el-menu-item.is-active)::before {
  /* Active indicator glow */
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%) scaleX(0.6);
  width: 20px;
  height: 2px;
  background: var(--rh-primary);
  filter: blur(2px);
  opacity: 0.4;
  border-radius: 1px;
  transition: transform var(--rh-duration-normal) var(--rh-transition-spring);
}

/* ── Right Section ── */

.navbar-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 4px;
  padding-left: 12px;
}

/* Theme Toggle Button */

.theme-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: var(--rh-radius-sm);
  color: var(--rh-text-secondary);
  transition: var(--rh-transition-all-normal);
}

.theme-toggle:hover {
  color: var(--rh-text-primary);
  background: var(--rh-bg-hover);
}

.theme-toggle :deep(.el-icon) {
  font-size: 18px;
}

/* ── User Trigger ── */

.user-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 5px 10px 5px 6px;
  height: 36px;
  border-radius: 999px;
  border: 1px solid transparent;
  transition: var(--rh-transition-all-normal);
  user-select: none;
}

.user-trigger:hover {
  background: var(--rh-bg-hover);
  border-color: var(--rh-border-faint);
}

.user-trigger.is-open {
  background: var(--rh-bg-inset);
  border-color: var(--rh-border);
}

.user-avatar {
  background: linear-gradient(135deg, var(--rh-primary), var(--rh-primary-hover));
  color: #ffffff;
  font-weight: 600;
  flex-shrink: 0;
}

.user-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--rh-text-primary);
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-chevron {
  color: var(--rh-text-tertiary);
  font-size: 12px;
  transition: transform var(--rh-duration-normal) var(--rh-transition-normal);
}

.user-trigger.is-open .user-chevron {
  transform: rotate(180deg);
}

@media (max-width: 768px) {
  .user-name,
  .user-chevron {
    display: none;
  }
}
</style>

<!-- Popper styles (teleported to body, non-scoped) -->

<style>
.user-menu-popper.el-popper {
  border-radius: var(--rh-radius-md) !important;
  box-shadow: var(--rh-shadow-lg) !important;
  border: 1px solid var(--rh-border) !important;
  padding: 8px;
}

.user-menu-popper .user-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px 14px;
  margin-bottom: 6px;
  border-bottom: 1px solid var(--rh-border);
}

.user-card-avatar {
  background: linear-gradient(135deg, var(--rh-primary), var(--rh-primary-hover));
  color: #ffffff;
  font-weight: 600;
  flex-shrink: 0;
}

.user-card-meta {
  min-width: 0;
}

.user-card-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--rh-text-primary);
  line-height: 1.35;
}

.user-card-email {
  font-size: 12px;
  color: var(--rh-text-tertiary);
  line-height: 1.35;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-menu-popper .el-dropdown-menu {
  padding: 4px !important;
}

.user-menu-popper .el-dropdown-menu__item {
  display: flex;
  align-items: center;
  gap: 8px;
  border-radius: var(--rh-radius-sm);
  padding: 8px 12px;
  color: var(--rh-text-secondary);
  font-weight: 500;
  transition: var(--rh-transition-all-normal);
}

.user-menu-popper .el-dropdown-menu__item:hover {
  background: var(--rh-bg-hover);
  color: var(--rh-primary);
}

.user-menu-popper .user-menu-logout.el-dropdown-menu__item:hover {
  background: rgba(220, 38, 38, 0.06);
  color: var(--rh-danger);
}

/* Dark mode logout hover */
[data-theme="dark"] .user-menu-popper .user-menu-logout.el-dropdown-menu__item:hover {
  background: rgba(248, 113, 113, 0.1);
}
</style>

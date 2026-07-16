<template>
  <el-menu
    mode="horizontal"
    :default-active="activeIndex"
    class="navbar"
    @select="handleSelect"
  >
    <div class="logo-item">
      <span class="logo-text">📚 ResourceHub</span>
    </div>

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

    <div class="navbar-right">
      <el-menu-item index="/settings">
        <el-icon><Setting /></el-icon>
      </el-menu-item>
      <el-dropdown trigger="click" @command="handleCommand">
        <span class="user-dropdown">
          <el-avatar :size="32" :icon="UserFilled" />
          <span class="username">{{ authStore.user?.username || '用户' }}</span>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="settings">
              <el-icon><Setting /></el-icon>设置
            </el-dropdown-item>
            <el-dropdown-item command="logout" divided>
              <el-icon><SwitchButton /></el-icon>退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </el-menu>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  Monitor, Document, MagicStick, Setting, UserFilled, SwitchButton,
} from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const activeIndex = computed(() => {
  const path = route.path
  if (path.startsWith('/notes')) return '/notes'
  if (path.startsWith('/prompts')) return '/prompts'
  if (path.startsWith('/dashboard')) return '/dashboard'
  if (path.startsWith('/settings')) return '/settings'
  return ''
})

function handleSelect(index: string) {
  if (index !== route.path) {
    router.push(index)
  }
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
.navbar {
  display: flex;
  align-items: center;
  padding: 0 24px;
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
  height: 60px;
  position: sticky;
  top: 0;
  z-index: 100;
}

.logo-item {
  cursor: default !important;
  opacity: 1 !important;
  font-weight: 700;
  font-size: 18px;
  padding: 0 32px 0 0 !important;
  background: transparent !important;
}

.logo-text {
  background: linear-gradient(135deg, #4f46e5, #6366f1);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.navbar :deep(.el-menu-item) {
  font-size: 14px;
  font-weight: 500;
  color: var(--rh-text-secondary);
  border-bottom: none !important;
  transition: var(--rh-transition);
  height: 60px;
  line-height: 60px;
}

.navbar :deep(.el-menu-item:hover) {
  color: var(--rh-primary);
  background: transparent !important;
}

.navbar :deep(.el-menu-item.is-active) {
  color: var(--rh-primary) !important;
  border-bottom: none !important;
  position: relative;
}

.navbar :deep(.el-menu-item.is-active)::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 20px;
  height: 3px;
  background: var(--rh-primary);
  border-radius: 2px 2px 0 0;
}

.navbar-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 4px;
}

.user-dropdown {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 0 12px;
  height: 60px;
  border-radius: 8px;
  transition: var(--rh-transition);
}

.user-dropdown:hover {
  background: var(--rh-bg-hover);
}

.username {
  font-size: 14px;
  font-weight: 500;
  color: var(--rh-text-secondary);
}
</style>

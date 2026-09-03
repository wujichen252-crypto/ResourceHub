import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore, isTokenExpired } from '../stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    redirect: '/dashboard',
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/notes',
    name: 'Notes',
    component: () => import('../views/Notes/NotesPage.vue'),
    meta: { requiresAuth: true },
  },
  // 旧路由向后兼容重定向
  {
    path: '/notes/:id',
    redirect: '/notes',
  },
  {
    path: '/notes/:id/edit',
    redirect: '/notes',
  },
  {
    path: '/prompts',
    name: 'Prompts',
    component: () => import('../views/Prompts/PromptList.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/prompts/new',
    name: 'NewPrompt',
    component: () => import('../views/Prompts/PromptEditor.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/prompts/:id',
    name: 'PromptDetail',
    component: () => import('../views/Prompts/PromptDetail.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/prompts/:id/edit',
    name: 'PromptEditor',
    component: () => import('../views/Prompts/PromptEditor.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/Settings.vue'),
    meta: { requiresAuth: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 导航守卫 — 未登录或令牌过期跳转到 /login
router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth) {
    // 无 access token → 未登录
    if (!authStore.accessToken) {
      next({ name: 'Login', query: { redirect: to.fullPath } })
      return
    }
    // access token 过期 → 尝试用 refresh token 静默刷新；失败则回登录页
    if (isTokenExpired(authStore.accessToken)) {
      if (authStore.refreshToken && !isTokenExpired(authStore.refreshToken)) {
        try {
          await authStore.refreshTokenAction()
          next()
          return
        } catch {
          // 刷新失败，走登出逻辑
        }
      }
      authStore.logout()
      next({ name: 'Login', query: { redirect: to.fullPath } })
      return
    }
    next()
    return
  }

  if (to.name === 'Login' && authStore.isAuthenticated) {
    next({ name: 'Dashboard' })
    return
  }

  next()
})

export default router

import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '../stores/auth'

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
    component: () => import('../views/Notes/NoteList.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/notes/:id',
    name: 'NoteDetail',
    component: () => import('../views/Notes/NoteDetail.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/notes/:id/edit',
    name: 'NoteEditor',
    component: () => import('../views/Notes/NoteEditor.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/prompts',
    name: 'Prompts',
    component: () => import('../views/Prompts/PromptList.vue'),
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

// 导航守卫 — 未登录跳转到 /login
router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (to.name === 'Login' && authStore.isAuthenticated) {
    next({ name: 'Dashboard' })
  } else {
    next()
  }
})

export default router

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

import './styles/theme.css'
import './styles/global.css'

import App from './App.vue'
import router from './router'

const app = createApp(App)

// Initialize theme before mount to prevent flash of wrong colors
try {
  const stored = localStorage.getItem('theme')
  const systemDark = window.matchMedia?.('(prefers-color-scheme: dark)').matches
  const theme = stored === 'dark' ? 'dark' : stored === 'light' ? 'light' : (systemDark ? 'dark' : 'light')
  // Already set via inline script in index.html; this is a sync fallback
  document.documentElement.setAttribute('data-theme', theme)
} catch {
  // localStorage may be unavailable; rely on index.html inline script
}

app.use(createPinia())
app.use(router)
app.use(ElementPlus)

app.mount('#app')

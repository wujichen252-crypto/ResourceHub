import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
// Element Plus 官方深色变量（需 html.dark 生效）：补齐按钮、下拉、分页、骨架等组件自身的深色取值
import 'element-plus/theme-chalk/dark/css-vars.css'

import './styles/theme.css'
import './styles/global.css'
import './styles/markdown.css'

import App from './App.vue'
import router from './router'

const app = createApp(App)

// 主题初始化由 index.html 内联脚本（防首屏闪色）与 composables/useTheme.ts 统一负责

app.use(createPinia())
app.use(router)
app.use(ElementPlus)

app.mount('#app')

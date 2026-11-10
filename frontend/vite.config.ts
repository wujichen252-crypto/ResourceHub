import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8800',
        changeOrigin: true,
      },
    },
  },
  build: {
    // 目标浏览器：支持 ES2019 的现代浏览器，避免为旧语法引入额外 polyfill
    target: 'es2019',
    // Element Plus 以全局方式注册（app.use），体积集中在单一 vendor 包，属预期内
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        /**
         * 手动分包：把体积大且更新频率低的第三方库拆成独立 chunk。
         * 收益：业务代码改动不会让 vendor 缓存失效，且入口包体积大幅下降。
         * 用函数按路径匹配而非写死包名，避免把未使用的子入口一并拉进产物。
         */
        manualChunks(id: string) {
          if (!id.includes('node_modules')) return
          if (id.includes('element-plus')) return 'vendor-element'
          if (id.includes('echarts')) return 'vendor-echarts'
          if (id.includes('markdown-it') || id.includes('dompurify')) return 'vendor-markdown'
          if (
            /node_modules[\\/](vue|vue-router|pinia|axios)[\\/]/.test(id) ||
            id.includes('@vue/')
          ) {
            return 'vendor-vue'
          }
        },
      },
    },
  },
})

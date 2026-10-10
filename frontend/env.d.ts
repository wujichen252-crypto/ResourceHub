/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

// echarts-wordcloud 官方未提供类型声明，此处补最小模块声明（副作用导入注册 series）
declare module 'echarts-wordcloud' {
  export {}
}

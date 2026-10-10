/**
 * ECharts 通用挂载 composable
 * - 运行时读取 CSS 变量，自动适配浅色/深色主题（监听 data-theme 变化重渲染）
 * - ResizeObserver 自适应容器尺寸
 * - onUnmounted 释放 ResizeObserver、MutationObserver 并 dispose 实例，杜绝内存泄漏
 */
import { onMounted, onUnmounted, watch, type Ref } from 'vue'
import * as echarts from 'echarts/core'
import { BarChart, HeatmapChart, LineChart, PieChart } from 'echarts/charts'
import {
  CalendarComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  VisualMapComponent,
} from 'echarts/components'
import 'echarts-wordcloud'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  BarChart,
  HeatmapChart,
  LineChart,
  PieChart,
  CalendarComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  VisualMapComponent,
  CanvasRenderer,
])

/** 从当前主题读取 CSS 变量值（图表颜色与全站 --rh-* 变量保持一致） */
export function themeVar(name: string, fallback = ''): string {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}

/** 全站图表共用基础配置（透明背景 + 主题文字色） */
export function baseChartOption() {
  return {
    backgroundColor: 'transparent',
    textStyle: { color: themeVar('--rh-text-secondary') },
    tooltip: {
      backgroundColor: themeVar('--rh-bg-elevated', '#fff'),
      borderColor: themeVar('--rh-border', '#ddd'),
      textStyle: { color: themeVar('--rh-text-primary') },
    },
  }
}

export interface UseChartOptions {
  /** 生成完整 ECharts option 的工厂（主题变化/数据变化时重新调用） */
  buildOption: () => Record<string, unknown>
  /** option 依赖的响应式数据源，变化时 setOption */
  watchSource?: Ref<unknown>
  /** 图表点击事件回调 */
  onClick?: (name: string) => void
}

export function useChart(elRef: Ref<HTMLElement | null | undefined>, opts: UseChartOptions) {
  let chart: echarts.ECharts | null = null
  let resizeObserver: ResizeObserver | null = null
  let themeObserver: MutationObserver | null = null

  function render() {
    if (!chart) return
    chart.setOption(opts.buildOption(), true)
  }

  function setup(el: HTMLElement) {
    chart = echarts.init(el)
    render()
    if (opts.onClick) {
      chart.on('click', (params) => {
        const name = typeof params.name === 'string' ? params.name : ''
        if (name) opts.onClick!(name)
      })
    }

    // 容器尺寸变化自适应
    resizeObserver = new ResizeObserver(() => chart?.resize())
    resizeObserver.observe(el)

    // 主题切换（html[data-theme]）时重读 CSS 变量并重渲染
    themeObserver = new MutationObserver(render)
    themeObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme'],
    })
  }

  onMounted(() => {
    if (elRef.value) setup(elRef.value)
  })

  // 容器由 v-if 延迟创建时（如数据加载后才渲染），出现后再初始化
  watch(elRef, (el) => {
    if (el && !chart) setup(el)
  })

  if (opts.watchSource) {
    watch(opts.watchSource, render, { deep: true })
  }

  onUnmounted(() => {
    resizeObserver?.disconnect()
    themeObserver?.disconnect()
    chart?.dispose()
    chart = null
  })

  return { render }
}

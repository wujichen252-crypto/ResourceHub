import { ref, onMounted } from 'vue'

/**
 * 带动画效果的数字计数 Composable
 * @param target 目标数值
 * @param duration 动画持续时间(ms)，默认 800ms
 * @returns 当前数值的响应式引用
 */
export function useAnimatedCounter(target: number, duration = 800) {
  const current = ref(0)
  let startTime: number | null = null

  function animate(timestamp: number) {
    if (!startTime) startTime = timestamp
    const progress = Math.min((timestamp - startTime) / duration, 1)
    // easeOutExpo easing
    const eased = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress)
    current.value = Math.round(eased * target)
    if (progress < 1) requestAnimationFrame(animate)
  }

  onMounted(() => requestAnimationFrame(animate))

  return current
}

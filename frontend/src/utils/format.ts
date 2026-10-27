/**
 * 日期格式化工具 —— 全站统一时间展示格式。
 * 原先各页面各自实现（toLocaleString / toLocaleDateString / 手拼字符串 / 相对时间）共 5 套写法，
 * 此处收敛为三种语义：绝对日期、绝对日期时间、相对时间。
 */

/** 可接受的输入类型：ISO 字符串 / 时间戳 / Date 对象 */
type DateInput = string | number | Date | null | undefined

/** 将后端返回的时间字符串 / 时间戳解析为 Date；空值或非法值返回 null */
function toDate(value?: DateInput): Date | null {
  if (value === null || value === undefined || value === '') return null
  // 纯日期字符串（YYYY-MM-DD）按本地时区解析，避免被当作 UTC 造成跨时区偏移一天
  if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const d = new Date(`${value}T00:00:00`)
    return Number.isNaN(d.getTime()) ? null : d
  }
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? null : d
}

/** 绝对日期：2026-10-20 */
export function formatDate(value?: DateInput): string {
  const d = toDate(value)
  if (!d) return ''
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${month}-${day}`
}

/** 绝对日期时间：2026-10-20 14:30 */
export function formatDateTime(value?: DateInput): string {
  const d = toDate(value)
  if (!d) return ''
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${formatDate(d)} ${hh}:${mm}`
}

/** 相对时间：刚刚 / 5 分钟前 / 3 小时前 / 2 天前；超过 30 天回退为绝对日期 */
export function formatRelative(value?: DateInput): string {
  const d = toDate(value)
  if (!d) return ''
  const diff = Date.now() - d.getTime()
  if (diff < 0) return formatDate(d)
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return '刚刚'
  if (mins < 60) return `${mins} 分钟前`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours} 小时前`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days} 天前`
  return formatDate(d)
}

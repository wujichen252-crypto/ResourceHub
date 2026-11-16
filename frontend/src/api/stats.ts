import http from './http'

/** 标签云条目 */
export interface TagItem {
  name: string
  value: number
}

/** 创作趋势单日条目 */
export interface TrendPoint {
  date: string // YYYY-MM-DD
  notes: number
  prompts: number
}

/** 分类分布条目 */
export interface DistributionItem {
  name: string
  value: number
}

/** 使用热力图单日条目 */
export interface HeatmapPoint {
  date: string // YYYY-MM-DD
  count: number
}

/** /api/stats/overview 响应契约 */
export interface StatsOverview {
  tag_cloud: TagItem[]
  creation_trend: TrendPoint[]
  category_distribution: DistributionItem[]
  usage_heatmap: HeatmapPoint[]
}

/** 往年今日笔记条目 */
export interface OnThisDayItem {
  id: number
  title: string
  years_ago: number
  created_at: string
}

/** 昨日遗留任务条目 */
export interface PendingTaskItem {
  note_id: number
  note_title: string
  task: string
}

/** /api/stats/daily-review 响应契约 */
export interface DailyReview {
  on_this_day: OnThisDayItem[]
  on_this_day_total: number
  this_week: number
  streak: number
  pending_tasks: PendingTaskItem[]
}

export const statsApi = {
  overview(): Promise<StatsOverview> {
    return http.get('/stats/overview')
  },

  dailyReview(): Promise<DailyReview> {
    return http.get('/stats/daily-review')
  },
}

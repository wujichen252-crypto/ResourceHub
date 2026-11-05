/**
 * 行级 LCS 文本对比工具
 *
 * 输出结构与后端版本对比接口（DiffSegment）保持一致，
 * 供自动优化器对比「基线内容 vs 候选内容」等无版本号的场景复用。
 */

export interface DiffSegment {
  type: 'equal' | 'insert' | 'delete'
  value: string
}

/** 把文本按行拆分（统一换行符，丢弃行尾空行的歧义由渲染层兜底） */
function splitLines(text: string): string[] {
  return text.replace(/\r\n/g, '\n').split('\n')
}

/**
 * 对两段文本做行级 diff：
 * 经典 LCS 动态规划，提示词正文通常只有几十行，规模完全可控。
 */
export function diffLines(before: string, after: string): DiffSegment[] {
  const a = splitLines(before)
  const b = splitLines(after)

  // LCS 长度表
  const rows = a.length
  const cols = b.length
  const table: number[][] = Array.from({ length: rows + 1 }, () => new Array(cols + 1).fill(0))
  for (let i = rows - 1; i >= 0; i--) {
    for (let j = cols - 1; j >= 0; j--) {
      table[i][j] = a[i] === b[j] ? table[i + 1][j + 1] + 1 : Math.max(table[i + 1][j], table[i][j + 1])
    }
  }

  // 回溯生成段序列，相邻同类型行合并为一个段
  const segments: DiffSegment[] = []
  const push = (type: DiffSegment['type'], value: string) => {
    const last = segments[segments.length - 1]
    if (last && last.type === type) {
      last.value += '\n' + value
    } else {
      segments.push({ type, value })
    }
  }

  let i = 0
  let j = 0
  while (i < rows && j < cols) {
    if (a[i] === b[j]) {
      push('equal', a[i])
      i++
      j++
    } else if (table[i + 1][j] >= table[i][j + 1]) {
      push('delete', a[i])
      i++
    } else {
      push('insert', b[j])
      j++
    }
  }
  while (i < rows) {
    push('delete', a[i])
    i++
  }
  while (j < cols) {
    push('insert', b[j])
    j++
  }

  return segments
}

/** diff 段的新增 / 删除行数统计 */
export function diffStats(segments: DiffSegment[]): { added: number; removed: number } {
  let added = 0
  let removed = 0
  for (const seg of segments) {
    if (seg.type === 'insert') added += seg.value.split('\n').length
    else if (seg.type === 'delete') removed += seg.value.split('\n').length
  }
  return { added, removed }
}

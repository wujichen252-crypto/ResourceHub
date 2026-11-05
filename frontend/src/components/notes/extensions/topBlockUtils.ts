/**
 * topBlockUtils.ts — 顶层块（doc 第一层子节点）操作工具
 *
 * 避免"块序号=文档位置"的错误假设（不同节点长度不同），
 * 所有重排都以 ProseMirror position 为基准。
 */
import type { Editor } from '@tiptap/core'

const TOP_BLOCK_TYPES = new Set([
  'paragraph', 'heading', 'bulletList', 'orderedList', 'taskList',
  'blockquote', 'codeBlock', 'table', 'horizontalRule', 'image',
])

/** 判断一个 node 是否是 doc 第一层可能出现的顶层块类型 */
export function isTopBlockNode(nodeType: string): boolean {
  return TOP_BLOCK_TYPES.has(nodeType)
}

/**
 * 从编辑器 DOM 的事件目标向上寻找带 data-block-id 的最近祖先。
 * 返回 { el, pos: ProseMirror doc position } 或 null。
 */
export function findTopBlockFromDom(
  editor: Editor,
  target: HTMLElement,
): { el: HTMLElement; pos: number; nodeSize: number } | null {
  let el: HTMLElement | null = target
  while (el && !el.hasAttribute?.('data-block-id')) {
    el = el.parentElement
    if (!el || el === editor.view.dom) return null
  }
  if (!el) return null

  const pos = editor.view.posAtDOM(el, 0)
  if (pos < 0) return null

  const node = editor.state.doc.nodeAt(pos)
  if (!node || !isTopBlockNode(node.type.name)) return null
  return { el, pos, nodeSize: node.nodeSize }
}

/** 顶层块范围：[pos, pos + nodeSize)，不含两端 margin */
export function topBlockRange(pos: number, nodeSize: number) {
  return { from: pos, to: pos + nodeSize }
}

/**
 * 将 fromPos 处的顶层块移动到 targetPos。
 * targetPos 应该是目标块的起始位置（插入到其之前）。
 * 使用单个 transaction，保证一次 undo 即可回退。
 */
export function moveTopBlock(editor: Editor, fromPos: number, targetPos: number) {
  const tr = editor.state.tr
  const node = editor.state.doc.nodeAt(fromPos)
  if (!node || !isTopBlockNode(node.type.name)) return

  // 若目标在源块范围内则跳过（自身不插到自己里面）
  const fromEnd = fromPos + node.nodeSize
  if (targetPos >= fromPos && targetPos < fromEnd) return

  // 先 delete from 区域，再根据偏移后的 targetPos insert
  // 若 targetPos > fromPos，delete 后 targetPos 会左移 from.nodeSize
  let adjustedTarget = targetPos
  if (targetPos > fromPos) {
    adjustedTarget = targetPos - node.nodeSize
  }

  tr.delete(fromPos, fromEnd)
  tr.insert(adjustedTarget, node)
  tr.scrollIntoView()

  editor.view.dispatch(tr)
}

/**
 * ProseMirror document position → 对应的 DOMRect（left/top/right/bottom）。
 * 用于悬浮拖拽手柄的定位。
 */
export function posToDomRect(editor: Editor, pos: number): DOMRect | null {
  const coords = editor.view.coordsAtPos(pos)
  return {
    left: coords.left,
    top: coords.top,
    right: coords.right,
    bottom: coords.bottom,
    width: coords.right - coords.left,
    height: coords.bottom - coords.top,
    toJSON() {
      return {
        left: this.left, top: this.top, right: this.right, bottom: this.bottom,
        width: this.width, height: this.height,
      }
    },
  } as DOMRect
}

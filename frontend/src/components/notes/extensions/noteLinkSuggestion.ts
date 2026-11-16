/**
 * [[ 笔记自动补全：基于 @tiptap/suggestion + 原生 DOM 下拉
 *
 * - 触发字符 `[[`，空 query 展示最近笔记
 * - 防抖查询 /api/notes（个人空间），键盘 ↑↓ 选择、Enter 确认、Esc 关闭
 * - 下拉渲染在 body 上（浮动层），样式走 --rh-* 令牌（见 global.css .rh-suggest-*）
 */
import { Extension } from '@tiptap/core'
import type { Editor, Range } from '@tiptap/core'
import { PluginKey } from '@tiptap/pm/state'
import Suggestion, { type SuggestionProps, type SuggestionKeyDownProps } from '@tiptap/suggestion'
import { notesApi } from '../../../api/notes'
import type { Note } from '../../../api/notes'

interface NoteSuggestionItem {
  id: number
  title: string
}

const SEARCH_DEBOUNCE_MS = 200
const SUGGEST_LIMIT = 8

// 当前已解析的候选（onKeyDown 阶段取用）
let lastItems: NoteSuggestionItem[] = []

export const NoteLinkSuggestion = Extension.create({
  name: 'noteLinkSuggestion',

  addProseMirrorPlugins() {
    const editor: Editor = this.editor

    return [
      Suggestion({
        editor,
        // 独立插件 key：SlashCommand 已占用默认的 suggestion key，
        // 重名会导致 ProseMirror 抛 "Adding different instances of a keyed plugin"，编辑器无法创建
        pluginKey: new PluginKey('noteLinkSuggestion'),
        char: '[[',
        startOfLine: false,
        // 代码块与行内代码中不触发
        allow: ({ state, range }) => {
          const $from = state.doc.resolve(range.from)
          if ($from.parent.type.spec.code) return false
          return !$from.marks().some((mark) => mark.type.name === 'code')
        },
        items: ({ query }): Promise<NoteSuggestionItem[]> =>
          new Promise((resolve) => {
            if (searchTimer) clearTimeout(searchTimer)
            searchTimer = setTimeout(async () => {
              const params: { search?: string; page_size: number } = { page_size: SUGGEST_LIMIT }
              if (query.trim()) params.search = query.trim()
              try {
                const data = await notesApi.list(params)
                lastItems = data.items.map((note: Note) => ({ id: note.id, title: note.title }))
              } catch {
                lastItems = []
              }
              resolve(lastItems)
            }, SEARCH_DEBOUNCE_MS)
          }),
        command: ({
          editor: ed,
          range,
          props: item,
        }: {
          editor: Editor
          range: Range
          props: NoteSuggestionItem
        }) => {
          // 插入 chip + 尾随空格，保持输入连续性
          ed.chain()
            .focus()
            .insertContentAt(range, [
              {
                type: 'noteLink',
                attrs: { title: item.title, noteId: item.id },
              },
              { type: 'text', text: ' ' },
            ])
            .run()
        },
        render: renderSuggestionMenu,
      }),
    ]
  },
})

// ── 原生 DOM 下拉渲染 ──────────────────────────────

let searchTimer: ReturnType<typeof setTimeout> | null = null
let lastQuery = ''
let selectedIndex = 0
let popup: HTMLDivElement | null = null
let activeCommand: ((item: NoteSuggestionItem) => void) | null = null

function renderList(items: NoteSuggestionItem[], query: string) {
  if (!popup) return
  // query 变化时复位选中项，避免键盘焦点落在已被过滤掉的条目上
  if (query !== lastQuery) selectedIndex = 0
  lastQuery = query
  popup.innerHTML = ''
  if (!items.length) {
    const empty = document.createElement('div')
    empty.className = 'rh-suggest-empty'
    empty.textContent = '没有匹配的笔记'
    popup.appendChild(empty)
    return
  }
  items.forEach((item, index) => {
    const row = document.createElement('button')
    row.type = 'button'
    row.className = 'rh-suggest-item' + (index === selectedIndex ? ' is-active' : '')
    row.textContent = item.title
    row.addEventListener('mousedown', (event) => {
      // mousedown 先于编辑器 blur，避免下拉闪没
      event.preventDefault()
      activeCommand?.(item)
    })
    popup!.appendChild(row)
  })
}

function positionMenu(props: SuggestionProps<NoteSuggestionItem>) {
  if (!popup) return
  const rect = props.clientRect?.()
  if (!rect) return
  const menuHeight = popup.offsetHeight || 220
  const flipUp = rect.bottom + menuHeight + 8 > window.innerHeight
  popup.style.left = `${rect.left}px`
  if (flipUp) {
    popup.style.bottom = `${window.innerHeight - rect.top + 6}px`
    popup.style.top = 'auto'
  } else {
    popup.style.top = `${rect.bottom + 6}px`
    popup.style.bottom = 'auto'
  }
}

function renderSuggestionMenu() {
  return {
    onStart(props: SuggestionProps<NoteSuggestionItem>) {
      popup = document.createElement('div')
      popup.className = 'rh-suggest-menu'
      popup.setAttribute('role', 'listbox')
      popup.setAttribute('aria-label', '笔记链接建议')
      document.body.appendChild(popup)
      activeCommand = props.command
      renderList(props.items, props.query)
      positionMenu(props)
    },
    onUpdate(props: SuggestionProps<NoteSuggestionItem>) {
      activeCommand = props.command
      renderList(props.items, props.query)
      positionMenu(props)
    },
    onKeyDown({ event }: SuggestionKeyDownProps) {
      if (event.key === 'ArrowDown') {
        if (lastItems.length) {
          selectedIndex = (selectedIndex + 1) % lastItems.length
          renderList(lastItems, lastQuery)
        }
        return true
      }
      if (event.key === 'ArrowUp') {
        if (lastItems.length) {
          selectedIndex = (selectedIndex - 1 + lastItems.length) % lastItems.length
          renderList(lastItems, lastQuery)
        }
        return true
      }
      if (event.key === 'Enter') {
        const item = lastItems[selectedIndex]
        if (item) activeCommand?.(item)
        return true
      }
      if (event.key === 'Escape') {
        popup?.remove()
        popup = null
        return true
      }
      return false
    },
    onExit() {
      if (searchTimer) {
        clearTimeout(searchTimer)
        searchTimer = null
      }
      popup?.remove()
      popup = null
      activeCommand = null
      lastQuery = ''
    },
  }
}

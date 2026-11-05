/**
 * BlockId Extension — 给每个顶层块注入稳定的 data-block-id，
 * 为反链锚点 / 评论定位 / 拖拽重排提供基准。
 */
import { Extension } from '@tiptap/core'
import { Plugin, PluginKey } from '@tiptap/pm/state'
import type { EditorState, Transaction } from '@tiptap/pm/state'

function genId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID().slice(0, 12).replace(/-/g, '')
  }
  return Math.random().toString(36).slice(2, 14)
}

const PLUGIN_KEY = new PluginKey('blockId')

export const BlockId = Extension.create<{ attribute: string }>({
  name: 'blockId',

  addOptions() {
    return { attribute: 'data-block-id' }
  },

  addGlobalAttributes() {
    return [
      {
        types: [
          'paragraph', 'heading', 'bulletList', 'orderedList', 'taskList',
          'blockquote', 'codeBlock', 'table', 'horizontalRule', 'image',
          'taskItem', 'listItem',
        ],
        attributes: {
          id: {
            default: null,
            parseHTML: (el) =>
              (el as HTMLElement).getAttribute(this.options.attribute),
            renderHTML: (attrs) => {
              if (!attrs.id) return {}
              return { [this.options.attribute]: attrs.id }
            },
          },
        },
      },
    ]
  },

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: PLUGIN_KEY,
        appendTransaction(
          _trs: readonly Transaction[],
          _oldState: EditorState,
          newState: EditorState,
        ) {
          const doc = newState.doc
          if (doc.childCount === 0) return null

          let changed = false
          let newTr = newState.tr

          doc.forEach((block, offset) => {
            if (block.attrs?.id) return
            const id = genId()
            newTr = newTr.setNodeMarkup(offset, block.type, {
              ...block.attrs,
              id,
            })
            changed = true
          })

          return changed ? newTr : null
        },
      }),
    ]
  },
})

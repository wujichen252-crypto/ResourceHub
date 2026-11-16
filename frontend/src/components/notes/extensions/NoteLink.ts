/**
 * 笔记双向链接节点（原子内联节点）
 *
 * 设计参考 aarkue/tiptap-wikilink-extension 与 TipTap Mention：
 * - 原子节点（atom: true）：chip 不可部分编辑，标题与属性永远一致
 * - attrs.noteId 优先（Logseq/SiYuan 的教训：ID 链接不受目标改名影响）
 * - 手输 [[标题]] 由输入规则自动转换为 chip；无匹配笔记时 noteId 为空，
 *   渲染为"待创建"样式，点击后由外层提供一键创建
 */
import { Node, mergeAttributes, nodeInputRule } from '@tiptap/core'

export interface NoteLinkAttrs {
  title: string
  noteId: number | null
}

export const NoteLink = Node.create({
  name: 'noteLink',
  inline: true,
  group: 'inline',
  atom: true,
  selectable: true,

  addAttributes() {
    return {
      title: {
        default: '',
        parseHTML: (element) => element.getAttribute('data-note-title') || '',
        renderHTML: (attributes) => ({ 'data-note-title': attributes.title }),
      },
      noteId: {
        default: null,
        parseHTML: (element) => {
          const value = element.getAttribute('data-note-id')
          return value ? Number(value) : null
        },
        renderHTML: (attributes) =>
          attributes.noteId ? { 'data-note-id': String(attributes.noteId) } : {},
      },
    }
  },

  parseHTML() {
    return [{ tag: 'span[data-type="noteLink"]' }]
  },

  renderHTML({ node, HTMLAttributes }) {
    return [
      'span',
      mergeAttributes(
        {
          'data-type': 'noteLink',
          class: 'note-wikilink',
        },
        HTMLAttributes,
      ),
      node.attrs.title,
    ]
  },

  addInputRules() {
    return [
      nodeInputRule({
        find: /\[\[([^\[\]]+)\]\]$/,
        type: this.type,
        getAttributes: (match) => ({
          title: (match[match.length - 1] || '').trim(),
          noteId: null,
        }),
      }),
    ]
  },
})

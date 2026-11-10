/**
 * SlashCommand Extension — @tiptap/suggestion + VueRenderer
 *
 * 输入 / 触发块类型菜单（≥10 种），键盘 ↑↓ 切换 / Enter 执行 / Esc 关闭。
 * 采用 v3 推荐路径：props.mount() 让 Suggestion 插件托管悬浮定位，
 * VueRenderer 只负责把 SlashMenu.vue 渲染到 DOM。
 */
import { Extension } from '@tiptap/core'
import Suggestion, {
  type SuggestionProps,
  type SuggestionKeyDownProps,
} from '@tiptap/suggestion'
import { VueRenderer } from '@tiptap/vue-3'
import SlashMenu, { type SlashMenuItem } from '../SlashMenu.vue'
import { ElMessageBox } from 'element-plus'

export type SlashItem = SlashMenuItem

function withCommand(editor: any, range: any, insert: () => void) {
  editor.chain().focus().deleteRange(range).run()
  insert()
}

const ALL_ITEMS: SlashItem[] = [
  {
    title: '段落', description: '普通文字段落', icon: '¶', keywords: 'text paragraph p',
    command: ({ editor, range }) =>
      withCommand(editor, range, () =>
        editor.chain().focus().setNode('paragraph').run()),
  },
  {
    title: '标题 1', description: '大标题', icon: 'H1', keywords: 'h1 heading',
    shortcut: '⌘1',
    command: ({ editor, range }) =>
      withCommand(editor, range, () =>
        editor.chain().focus().toggleHeading({ level: 1 }).run()),
  },
  {
    title: '标题 2', description: '中标题', icon: 'H2', keywords: 'h2 heading',
    shortcut: '⌘2',
    command: ({ editor, range }) =>
      withCommand(editor, range, () =>
        editor.chain().focus().toggleHeading({ level: 2 }).run()),
  },
  {
    title: '标题 3', description: '小标题', icon: 'H3', keywords: 'h3 heading',
    shortcut: '⌘3',
    command: ({ editor, range }) =>
      withCommand(editor, range, () =>
        editor.chain().focus().toggleHeading({ level: 3 }).run()),
  },
  {
    title: '无序列表', description: '小圆点列表', icon: '•', keywords: 'bullet list ul',
    command: ({ editor, range }) =>
      withCommand(editor, range, () =>
        editor.chain().focus().toggleBulletList().run()),
  },
  {
    title: '有序列表', description: '1. 2. 3. 列表', icon: '1.', keywords: 'ordered list ol',
    command: ({ editor, range }) =>
      withCommand(editor, range, () =>
        editor.chain().focus().toggleOrderedList().run()),
  },
  {
    title: '任务列表', description: '可勾选任务', icon: '☐', keywords: 'task todo checkbox',
    command: ({ editor, range }) =>
      withCommand(editor, range, () =>
        editor.chain().focus().toggleTaskList().run()),
  },
  {
    title: '引用', description: '灰色侧边条引言', icon: '❝', keywords: 'quote blockquote',
    command: ({ editor, range }) =>
      withCommand(editor, range, () =>
        editor.chain().focus().toggleBlockquote().run()),
  },
  {
    title: '代码块', description: '等宽代码段', icon: '{ }', keywords: 'code pre',
    command: ({ editor, range }) =>
      withCommand(editor, range, () =>
        editor.chain().focus().toggleCodeBlock().run()),
  },
  {
    title: '分割线', description: '横隔线', icon: '—', keywords: 'hr divider',
    command: ({ editor, range }) =>
      withCommand(editor, range, () =>
        editor.chain().focus().setHorizontalRule().run()),
  },
  {
    title: '表格', description: '3×3 起的表格', icon: '⊞', keywords: 'table grid',
    command: ({ editor, range }) =>
      withCommand(editor, range, () =>
        editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()),
  },
  {
    title: '图片', description: '输入 URL 插入', icon: '🖼', keywords: 'image img picture',
    command: async ({ editor, range }) => {
      editor.chain().focus().deleteRange(range).run()
      try {
        const { value } = await ElMessageBox.prompt('图片 URL', '插入图片', {
          confirmButtonText: '插入',
          cancelButtonText: '取消',
          inputPlaceholder: 'https://...',
        })
        editor.chain().focus().setImage({ src: value }).run()
      } catch { /* 用户取消 */ }
    },
  },
]

function renderSlashMenu() {
  let component: VueRenderer | null = null
  let unmount: (() => void) | null = null

  return {
    onStart(props: SuggestionProps<SlashItem, SlashItem>) {
      component = new VueRenderer(SlashMenu, {
        props: {
          items: ALL_ITEMS,
          query: props.query,
          position: null,
          // 选中回调交给菜单直接调用：Suggestion 的 command 会走扩展配置里的
          // command → item.command({ editor, range })，range 由各 item 自行删除
          command: props.command,
        },
        editor: props.editor,
      })
      if (component.element) {
        // v3 推荐路径：让 Suggestion 插件托管浮层定位
        unmount = props.mount(component.element as HTMLElement)
      }
    },

    onUpdate(props: SuggestionProps<SlashItem, SlashItem>) {
      component?.updateProps({
        query: props.query,
        items: ALL_ITEMS,
        command: props.command,
      })
    },

    onKeyDown(_props: SuggestionKeyDownProps) {
      // SlashMenu 自己监听 document keydown —— 这里不拦截
      return false
    },

    onExit() {
      component?.destroy()
      component = null
      if (unmount) {
        unmount()
        unmount = null
      }
    },
  }
}

export const SlashCommand = Extension.create({
  name: 'slashCommand',

  addOptions() {
    return {
      suggestion: {
        char: '/',
        command: ({ editor, range, props }: any) => {
          props.command({ editor, range })
        },
        items: () => ALL_ITEMS,
        render: renderSlashMenu,
      },
    }
  },

  addProseMirrorPlugins() {
    return [
      Suggestion({
        editor: this.editor,
        ...this.options.suggestion,
      }),
    ]
  },
})

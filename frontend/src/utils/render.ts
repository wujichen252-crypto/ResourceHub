/**
 * 客户端侧模板渲染工具
 * 镜像后端 _render_template 逻辑，实现即时预览
 */

/**
 * 渲染模板：将模板中的 {{变量名}} 替换为对应的值
 */
export function renderTemplate(template: string, variables: Record<string, string>): string {
  return template.replace(/\{\{(\w+)\}\}/g, (match, name) => {
    return variables[name] !== undefined ? variables[name] : match
  })
}

/**
 * 从模板中提取所有 {{变量名}} 占位符
 */
export function extractVariables(template: string): string[] {
  const matches = template.match(/\{\{(\w+)\}\}/g)
  if (!matches) return []
  return [...new Set(matches.map((m) => m.replace(/\{\{|\}\}/g, '')))]
}

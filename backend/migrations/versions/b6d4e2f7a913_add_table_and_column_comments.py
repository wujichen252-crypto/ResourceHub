"""add_table_and_column_comments

Revision ID: b6d4e2f7a913
Revises: e5b9d2f4c817
Create Date: 2026-11-05 15:00:00.000000

为全部 22 张表补齐表注释与字段中文注释。

只写注释，不改任何表结构与数据：
- MySQL 的列注释只能通过 ALTER TABLE ... MODIFY COLUMN 重述列定义实现，
  因此每条 MODIFY 均按迁移历史一字不差地重述 类型/可空/默认值，
  不引入任何类型或约束变化；主键自增列同步重述 AUTO_INCREMENT。
- SQLite（本地测试库）不支持列级注释，直接跳过，不影响 pytest。
- 表注释与列注释文本与 app/models/*.py 中的 comment= 保持一致。
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b6d4e2f7a913"
down_revision: Union[str, None] = "a7c3e91d5b48"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ── 列规格：(列名, MySQL 类型, 是否可空, 默认值 SQL 片段或 None, 注释) ──
# 默认值片段照抄各历史迁移中的 server_default，保证重述后与原库一致。
TABLES: dict[str, tuple[str, list[tuple[str, str, bool, str | None, str]]]] = {
    "users": (
        "用户表：账号、登录凭证与时间戳",
        [
            ("id", "INT", False, None, "用户 ID，主键自增"),
            ("username", "VARCHAR(50)", False, None, "用户名，全站唯一"),
            ("email", "VARCHAR(100)", True, None, "邮箱，唯一，可为空"),
            ("password_hash", "VARCHAR(255)", False, None, "密码哈希（不存明文）"),
            ("avatar", "VARCHAR(255)", True, None, "头像 URL，可空"),
            ("created_at", "DATETIME", False, "CURRENT_TIMESTAMP", "创建时间"),
            ("updated_at", "DATETIME", False, "CURRENT_TIMESTAMP", "更新时间"),
        ],
    ),
    "categories": (
        "分类表：树形分类，同时服务笔记与提示词（type 区分）",
        [
            ("id", "INT", False, None, "分类 ID，主键自增"),
            ("user_id", "INT", False, None, "所属用户 ID（用户删除时级联删除）"),
            ("name", "VARCHAR(100)", False, None, "分类名称"),
            ("type", "VARCHAR(20)", False, None, "分类用途：note=笔记分类 / prompt=提示词分类"),
            ("parent_id", "INT", True, None, "父分类 ID（自引用，NULL 为顶级分类；父级删除后置空）"),
            ("sort_order", "INT", False, None, "同级排序序号，越小越靠前"),
            ("created_at", "DATETIME", False, "CURRENT_TIMESTAMP", "创建时间"),
        ],
    ),
    "notes": (
        "笔记表：用户笔记正文、标签与广场分享状态",
        [
            ("id", "INT", False, None, "笔记 ID，主键自增"),
            ("user_id", "INT", False, None, "所属用户 ID（用户删除时级联删除）"),
            ("title", "VARCHAR(255)", False, None, "笔记标题"),
            ("content", "TEXT", True, None, "笔记正文（Markdown）"),
            ("category_id", "INT", True, None, "所属分类 ID（分类删除后置空）"),
            ("tags", "VARCHAR(500)", True, None, "标签，JSON 数组字符串"),
            ("is_pinned", "TINYINT(1)", False, None, "是否置顶"),
            ("visibility", "VARCHAR(20)", False, "'private'", "可见性：private=私有 / public=广场公开"),
            ("published_at", "DATETIME", True, None, "公开发布时间，未发布为 NULL"),
            ("source_user_id", "INT", True, None, "fork 来源用户 ID（无外键，作者删号不影响副本）"),
            ("source_content_id", "INT", True, None, "fork 来源笔记 ID（无外键）"),
            ("source_username", "VARCHAR(50)", True, None, "fork 来源用户名快照（冗余存储用于展示）"),
            ("created_at", "DATETIME", False, "CURRENT_TIMESTAMP", "创建时间"),
            ("updated_at", "DATETIME", False, "CURRENT_TIMESTAMP", "更新时间"),
        ],
    ),
    "prompts": (
        "提示词表：AI 提示词正文、变量定义与广场分享状态",
        [
            ("id", "INT", False, None, "提示词 ID，主键自增"),
            ("user_id", "INT", False, None, "所属用户 ID（用户删除时级联删除）"),
            ("title", "VARCHAR(255)", False, None, "提示词标题"),
            ("description", "VARCHAR(500)", True, None, "提示词简介，可空"),
            ("content", "TEXT", False, None, "提示词正文（支持 {{变量}} 占位符）"),
            ("category_id", "INT", True, None, "所属分类 ID（分类删除后置空）"),
            ("variables", "VARCHAR(500)", True, None, "变量定义，JSON 数组字符串"),
            ("tags", "VARCHAR(500)", True, None, "标签，JSON 数组字符串"),
            ("is_favorite", "TINYINT(1)", False, None, "是否收藏"),
            ("usage_count", "INT", False, None, "累计使用次数"),
            ("visibility", "VARCHAR(20)", False, "'private'", "可见性：private=私有 / public=广场公开"),
            ("published_at", "DATETIME", True, None, "公开发布时间，未发布为 NULL"),
            ("source_user_id", "INT", True, None, "fork 来源用户 ID（无外键，作者删号不影响副本）"),
            ("source_content_id", "INT", True, None, "fork 来源提示词 ID（无外键）"),
            ("source_username", "VARCHAR(50)", True, None, "fork 来源用户名快照（冗余存储用于展示）"),
            ("created_at", "DATETIME", False, "CURRENT_TIMESTAMP", "创建时间"),
            ("updated_at", "DATETIME", False, "CURRENT_TIMESTAMP", "更新时间"),
        ],
    ),
    "prompt_versions": (
        "提示词版本历史表：类 Git 的版本快照（支持标签与分支）",
        [
            ("id", "INT", False, None, "版本 ID，主键自增"),
            ("prompt_id", "INT", False, None, "所属提示词 ID（级联删除）"),
            ("version_number", "INT", False, None, "版本号，提示词内自增"),
            ("title", "VARCHAR(255)", False, None, "该版本的标题快照"),
            ("description", "VARCHAR(500)", True, None, "该版本的简介快照"),
            ("content", "TEXT", False, None, "该版本的正文快照"),
            ("variables", "VARCHAR(500)", True, None, "该版本的变量定义，JSON 数组字符串"),
            ("tags", "VARCHAR(500)", True, None, "该版本的标签，JSON 数组字符串"),
            ("message", "VARCHAR(500)", True, None, "提交说明（类似 Git commit message）"),
            ("labels", "VARCHAR(500)", True, None, "版本标签，JSON 数组：如 [\"production\", \"staging\"]"),
            ("branch_name", "VARCHAR(100)", False, None, "所属分支名，默认 main"),
            ("created_at", "DATETIME", False, "CURRENT_TIMESTAMP", "创建时间"),
        ],
    ),
    "prompt_presets": (
        "提示词变量预设表：保存一套变量取值，一键填入",
        [
            ("id", "INT", False, None, "预设 ID，主键自增"),
            ("prompt_id", "INT", False, None, "所属提示词 ID（级联删除）"),
            ("name", "VARCHAR(100)", False, None, "预设名称"),
            ("values", "TEXT", False, None, "变量取值，JSON 对象字符串（键为变量名）"),
            ("created_at", "DATETIME", False, "CURRENT_TIMESTAMP", "创建时间"),
        ],
    ),
    "prompt_usage_logs": (
        "提示词使用记录表：每次运行留痕，供使用分析面板统计",
        [
            ("id", "INT", False, None, "记录 ID，主键自增"),
            ("prompt_id", "INT", False, None, "被使用的提示词 ID（级联删除）"),
            ("user_id", "INT", False, None, "使用人用户 ID（级联删除）"),
            ("used_at", "DATETIME", False, "CURRENT_TIMESTAMP", "使用时间"),
        ],
    ),
    "note_likes": (
        "广场笔记点赞表：note_id+user_id 联合唯一，一人一篇最多一行",
        [
            ("id", "INT", False, None, "点赞 ID，主键自增"),
            ("note_id", "INT", False, None, "被点赞的笔记 ID（级联删除）"),
            ("user_id", "INT", False, None, "点赞用户 ID（级联删除）"),
            ("created_at", "DATETIME", False, "CURRENT_TIMESTAMP", "点赞时间"),
        ],
    ),
    "note_favorites": (
        "广场笔记收藏表：只读书签（区别于 fork 复制副本），note_id+user_id 联合唯一",
        [
            ("id", "INT", False, None, "收藏 ID，主键自增"),
            ("note_id", "INT", False, None, "被收藏的笔记 ID（级联删除）"),
            ("user_id", "INT", False, None, "收藏用户 ID（级联删除）"),
            ("created_at", "DATETIME", False, "CURRENT_TIMESTAMP", "收藏时间"),
        ],
    ),
    "note_chunks": (
        "笔记分块表：RAG 的最小检索单元，含向量索引",
        [
            ("id", "INT", False, None, "分块 ID，主键自增"),
            ("user_id", "INT", False, None, "所属用户 ID（级联删除）"),
            ("note_id", "INT", False, None, "所属笔记 ID（级联删除）"),
            ("chunk_index", "INT", False, None, "分块序号（文内从 0 开始，与 note_id 联合唯一）"),
            ("content", "TEXT", False, None, "分块正文"),
            ("content_hash", "VARCHAR(64)", True, None, "内容哈希，用于增量更新判重"),
            ("token_count", "INT", False, "0", "分块 token 数"),
            ("embedding", "TEXT", True, None, "分块向量（JSON 数组字符串，MySQL 无原生向量类型）"),
            ("embedding_model", "VARCHAR(64)", True, None, "生成该向量的嵌入模型名"),
            ("created_at", "DATETIME", False, "CURRENT_TIMESTAMP", "创建时间"),
            ("updated_at", "DATETIME", False, "CURRENT_TIMESTAMP", "更新时间"),
        ],
    ),
    "ai_conversations": (
        "AI 对话会话表：多轮问答的会话容器",
        [
            ("id", "INT", False, None, "会话 ID，主键自增"),
            ("user_id", "INT", False, None, "所属用户 ID（级联删除）"),
            ("title", "VARCHAR(255)", False, "'新对话'", "会话标题，默认「新对话」"),
            ("model", "VARCHAR(64)", True, None, "会话使用的对话模型名，可空"),
            ("message_count", "INT", False, "0", "会话内消息总数"),
            ("created_at", "DATETIME", False, "CURRENT_TIMESTAMP", "创建时间"),
            ("updated_at", "DATETIME", False, "CURRENT_TIMESTAMP", "更新时间"),
        ],
    ),
    "ai_messages": (
        "AI 对话消息表：检索引用与工具调用以 JSON 字符串留档",
        [
            ("id", "INT", False, None, "消息 ID，主键自增"),
            ("conversation_id", "INT", False, None, "所属会话 ID（级联删除）"),
            ("role", "VARCHAR(16)", False, None, "消息角色：user=用户 / assistant=助手 / tool=工具"),
            ("content", "TEXT", False, None, "消息正文"),
            ("citations", "TEXT", True, None, "检索引用来源，JSON 数组字符串，可空"),
            ("tool_calls", "TEXT", True, None, "工具调用记录，JSON 数组字符串，可空"),
            ("prompt_tokens", "INT", False, "0", "输入 token 数"),
            ("completion_tokens", "INT", False, "0", "输出 token 数"),
            ("latency_ms", "INT", False, "0", "响应耗时（毫秒）"),
            ("model", "VARCHAR(64)", True, None, "生成该消息的模型名，可空"),
            ("created_at", "DATETIME", False, "CURRENT_TIMESTAMP", "创建时间"),
        ],
    ),
    "ai_runs": (
        "Agent 运行轨迹表：完整事件序列可回放，写操作支持人在环确认",
        [
            ("id", "INT", False, None, "运行 ID，主键自增"),
            ("user_id", "INT", False, None, "所属用户 ID（级联删除）"),
            ("conversation_id", "INT", True, None, "关联会话 ID（会话删除后置空）"),
            ("goal", "TEXT", False, None, "本次 Agent 任务目标"),
            ("status", "VARCHAR(20)", False, "'running'",
             "运行状态：running=执行中 / waiting_confirmation=等待人工确认 / succeeded=成功 / failed=失败 / cancelled=已取消"),
            ("steps", "TEXT", False, None, "执行事件序列，JSON 数组字符串（可回放）"),
            ("step_count", "INT", False, "0", "已执行步数"),
            ("pending_action", "TEXT", True, None, "待人工确认的工具调用，JSON 字符串；确认后清除"),
            ("prompt_tokens", "INT", False, "0", "累计输入 token 数"),
            ("completion_tokens", "INT", False, "0", "累计输出 token 数"),
            ("error", "VARCHAR(500)", True, None, "失败原因，成功为 NULL"),
            ("created_at", "DATETIME", False, "CURRENT_TIMESTAMP", "创建时间"),
            ("finished_at", "DATETIME", True, None, "结束时间，未结束为 NULL"),
        ],
    ),
    "ai_usage_logs": (
        "AI 模型调用计量表：token 成本核算、配额限制与评测数据来源",
        [
            ("id", "INT", False, None, "日志 ID，主键自增"),
            ("user_id", "INT", False, None, "发起调用的用户 ID（级联删除）"),
            ("scene", "VARCHAR(32)", False, None,
             "调用场景：chat=对话 / agent=智能体 / embedding=向量化 / eval=评测 / optimize=自动优化"),
            ("model", "VARCHAR(64)", True, None, "被调用的模型名，可空"),
            ("prompt_tokens", "INT", False, "0", "输入 token 数"),
            ("completion_tokens", "INT", False, "0", "输出 token 数"),
            ("total_tokens", "INT", False, "0", "总 token 数（输入+输出）"),
            ("latency_ms", "INT", False, "0", "调用耗时（毫秒）"),
            ("success", "TINYINT(1)", False, "1", "调用是否成功"),
            ("error_code", "VARCHAR(64)", True, None, "失败错误码，成功为 NULL"),
            ("created_at", "DATETIME", False, "CURRENT_TIMESTAMP", "调用时间"),
        ],
    ),
    "prompt_eval_suites": (
        "提示词评测集表：一个提示词可拥有多套评测标准（Prompt 实验室）",
        [
            ("id", "INT", False, None, "评测集 ID，主键自增"),
            ("user_id", "INT", False, None, "所属用户 ID（级联删除）"),
            ("prompt_id", "INT", False, None, "被评测的提示词 ID（级联删除）"),
            ("name", "VARCHAR(191)", False, None, "评测集名称"),
            ("description", "VARCHAR(500)", True, None, "评测集说明，可空"),
            ("judge_model", "VARCHAR(64)", True, None, "LLM 评委模型名，为空则用默认模型评分"),
            ("created_at", "DATETIME", False, "CURRENT_TIMESTAMP", "创建时间"),
            ("updated_at", "DATETIME", False, "CURRENT_TIMESTAMP", "更新时间"),
        ],
    ),
    "prompt_eval_cases": (
        "提示词评测用例表：变量取值 + 期望输出 + 评分要点",
        [
            ("id", "INT", False, None, "用例 ID，主键自增"),
            ("suite_id", "INT", False, None, "所属评测集 ID（级联删除）"),
            ("variables", "TEXT", False, None, "变量取值，JSON 对象字符串（键为提示词变量名）"),
            ("expected_output", "TEXT", True, None, "期望输出（评分参考），可空"),
            ("rubric", "TEXT", True, None, "评分要点，可空"),
            ("created_at", "DATETIME", False, "CURRENT_TIMESTAMP", "创建时间"),
        ],
    ),
    "prompt_eval_results": (
        "提示词评测结果表：按版本聚合即可做 A/B 对比",
        [
            ("id", "INT", False, None, "结果 ID，主键自增"),
            ("suite_id", "INT", False, None, "所属评测集 ID（级联删除）"),
            ("case_id", "INT", False, None, "对应评测用例 ID（级联删除）"),
            ("prompt_version_id", "INT", True, None, "被测提示词版本 ID（版本删除后置空）"),
            ("model", "VARCHAR(64)", True, None, "被测模型名，可空"),
            ("output", "TEXT", False, None, "模型实际输出"),
            ("score", "FLOAT", True, None, "评委评分（0-100），未评分为 NULL"),
            ("judge_reason", "TEXT", True, None, "评委评语（扣分理由），可空"),
            ("latency_ms", "INT", False, "0", "生成耗时（毫秒）"),
            ("total_tokens", "INT", False, "0", "消耗总 token 数"),
            ("created_at", "DATETIME", False, "CURRENT_TIMESTAMP", "评测时间"),
        ],
    ),
    "prompt_optimization_runs": (
        "提示词自动优化会话表：以评测结果为输入的改写-评测闭环，状态可追溯",
        [
            ("id", "INT", False, None, "优化会话 ID，主键自增"),
            ("user_id", "INT", False, None, "所属用户 ID（级联删除）"),
            ("prompt_id", "INT", False, None, "被优化的提示词 ID（级联删除）"),
            ("suite_id", "INT", False, None, "优化所依据的评测集 ID（级联删除）"),
            ("status", "VARCHAR(20)", False, "'running'",
             "会话状态：running=优化中 / awaiting_review=等待人工采纳 / completed=已完成 / cancelled=已取消 / failed=失败"),
            ("round_number", "INT", False, "0", "当前轮次，从 0 开始"),
            ("max_rounds", "INT", False, "3", "最大优化轮数，默认 3"),
            ("score_threshold", "FLOAT", False, "80", "达标分数（达到即提前结束），默认 80"),
            ("temperature", "FLOAT", False, "0.3", "改写时模型温度，默认 0.3"),
            ("baseline_version_id", "INT", True, None, "基线版本 ID（未指定则用当前正文）"),
            ("baseline_content", "TEXT", True, None, "基线正文快照"),
            ("baseline_score", "FLOAT", True, None, "基线评测得分（0-100）"),
            ("baseline_detail", "TEXT", True, None, "基线逐用例评分明细，JSON 字符串"),
            ("candidate_content", "TEXT", True, None, "当前轮候选正文（AI 改写结果）"),
            ("candidate_score", "FLOAT", True, None, "当前轮候选评测得分（0-100）"),
            ("candidate_detail", "TEXT", True, None, "当前轮候选逐用例评分明细，JSON 字符串"),
            ("candidate_version_id", "INT", True, None, "候选被采纳后保存成的版本 ID"),
            ("analysis", "TEXT", True, None, "本轮 AI 诊断分析"),
            ("changelog", "VARCHAR(500)", True, None, "改动说明（采纳时作为版本的 commit message）"),
            ("total_tokens", "INT", False, "0", "整个优化会话累计消耗 token 数"),
            ("error_message", "VARCHAR(500)", True, None, "失败原因，成功为 NULL"),
            ("created_at", "DATETIME", False, "CURRENT_TIMESTAMP", "创建时间"),
            ("updated_at", "DATETIME", False, "CURRENT_TIMESTAMP", "更新时间"),
        ],
    ),
    "prompt_optimization_rounds": (
        "提示词自动优化轮次表：单轮历史快照（诊断→候选→评测→对比），供回放",
        [
            ("id", "INT", False, None, "轮次 ID，主键自增"),
            ("run_id", "INT", False, None, "所属优化会话 ID（级联删除）"),
            ("round_number", "INT", False, None, "轮次编号，会话内从 1 开始"),
            ("status", "VARCHAR(20)", False, "'completed'",
             "轮次状态：completed=完成 / skipped=作废（如变量漂移） / failed=失败"),
            ("candidate_content", "TEXT", True, None, "本轮候选正文快照"),
            ("candidate_score", "FLOAT", True, None, "本轮候选评测得分（0-100）"),
            ("reference_score", "FLOAT", True, None, "与之对比的基准分（基线或上一轮）"),
            ("analysis", "TEXT", True, None, "本轮 AI 诊断分析"),
            ("changelog", "VARCHAR(500)", True, None, "本轮改动说明"),
            ("snapshot", "TEXT", True, None, "逐用例对比明细快照，JSON 字符串"),
            ("total_tokens", "INT", False, "0", "本轮消耗 token 数"),
            ("created_at", "DATETIME", False, "CURRENT_TIMESTAMP", "创建时间"),
        ],
    ),
    "agent_profiles": (
        "智能体人格配置表：一个用户可有多条，MVP 只激活其中一条",
        [
            ("id", "INT", False, None, "人格配置 ID，主键自增"),
            ("user_id", "INT", False, None, "所属用户 ID（级联删除）"),
            ("name", "VARCHAR(50)", False, "'知识助手'", "智能体名称"),
            # 线上库 persona 实际无 DEFAULT（历史迁移声明与实库不一致），重述时保持无默认
            ("persona", "TEXT", False, None, "人设描述（写进系统提示词）"),
            ("tone", "VARCHAR(20)", False, "'严谨'", "语气风格，如：严谨 / 轻松"),
            ("expertise", "VARCHAR(200)", True, None, "专长领域，可空"),
            ("boundaries", "TEXT", True, None, "行为边界约束（禁止事项），可空"),
            ("greeting", "VARCHAR(200)", True, None, "开场问候语，可空"),
            ("is_default", "TINYINT(1)", False, "0", "是否为默认激活的人格"),
            ("created_at", "DATETIME", False, "CURRENT_TIMESTAMP", "创建时间"),
            ("updated_at", "DATETIME", False, "CURRENT_TIMESTAMP", "更新时间"),
        ],
    ),
    "agent_memories": (
        "智能体长期记忆表：从对话沉淀、可检索可衰减，一条一条独立管理",
        [
            ("id", "INT", False, None, "记忆 ID，主键自增"),
            ("user_id", "INT", False, None, "所属用户 ID（级联删除）"),
            ("profile_id", "INT", True, None, "关联人格 ID（人格删除后置空，记忆仍保留）"),
            ("memory_type", "VARCHAR(20)", False, "'fact'",
             "记忆类型：fact=事实 / preference=偏好 / goal=目标 / event=事件"),
            ("content", "TEXT", False, None, "记忆内容（一句完整的中文陈述）"),
            ("embedding", "TEXT", True, None, "记忆向量（JSON 数组字符串，MySQL 无原生向量类型）"),
            ("importance", "INT", False, "3", "重要度 1-5，默认 3；决定检索优先级与淘汰顺序"),
            ("source", "VARCHAR(20)", False, "'manual'", "来源：manual=用户手动添加 / auto=对话自动沉淀"),
            ("source_conversation_id", "INT", True, None, "来源会话 ID（故意无外键，会话清理后记忆仍保留）"),
            ("last_used_at", "DATETIME", True, None, "最近一次被检索使用的时间，未使用为 NULL"),
            ("use_count", "INT", False, "0", "累计被使用次数"),
            ("expires_at", "DATETIME", True, None, "过期时间，NULL 为永久有效"),
            ("created_at", "DATETIME", False, "CURRENT_TIMESTAMP", "创建时间"),
            ("updated_at", "DATETIME", False, "CURRENT_TIMESTAMP", "更新时间"),
        ],
    ),
    "agent_proactive_messages": (
        "智能体主动消息表：每日回顾、目标提醒等智能体主动发起的通知",
        [
            ("id", "INT", False, None, "消息 ID，主键自增"),
            ("user_id", "INT", False, None, "所属用户 ID（级联删除）"),
            ("kind", "VARCHAR(30)", False, "'daily_review'",
             "消息类型：daily_review=每日回顾 / stale_goal=目标久未推进"),
            ("title", "VARCHAR(200)", False, None, "消息标题"),
            ("content", "TEXT", False, None, "消息正文"),
            ("status", "VARCHAR(20)", False, "'unread'", "状态：unread=未读 / read=已读 / dismissed=已忽略"),
            ("source_ref", "VARCHAR(100)", True, None, "来源引用（如关联的笔记/记忆 ID），可空"),
            ("created_at", "DATETIME", False, "CURRENT_TIMESTAMP", "创建时间"),
        ],
    ),
}


def _build_alter_sql(table: str, table_comment: str, columns: list) -> str:
    """每张表拼一条 ALTER TABLE：表注释 + 各列 MODIFY（重述原定义，仅追加 COMMENT）"""
    parts: list[str] = [f"COMMENT='{table_comment}'"]
    for name, ctype, nullable, default, comment in columns:
        null_sql = "NULL" if nullable else "NOT NULL"
        default_sql = f" DEFAULT {default}" if default else ""
        # 所有表主键均为 INT AUTO_INCREMENT，重述时必须带上，否则自增会被移除
        auto = " AUTO_INCREMENT" if name == "id" else ""
        parts.append(
            f"MODIFY COLUMN `{name}` {ctype} {null_sql}{default_sql}{auto} COMMENT '{comment}'"
        )
    return f"ALTER TABLE `{table}`\n  " + ",\n  ".join(parts) + ";"


def upgrade() -> None:
    """仅追加表注释与列注释（MySQL）；SQLite 测试库不支持，直接跳过"""
    if op.get_bind().dialect.name != "mysql":
        return
    for table, (table_comment, columns) in TABLES.items():
        op.execute(_build_alter_sql(table, table_comment, columns))


def downgrade() -> None:
    """回滚仅清除注释（同样只动注释不动结构与数据）"""
    if op.get_bind().dialect.name != "mysql":
        return
    for table, (_, columns) in TABLES.items():
        parts: list[str] = ["COMMENT=''"]
        for name, ctype, nullable, default in [(c[0], c[1], c[2], c[3]) for c in columns]:
            null_sql = "NULL" if nullable else "NOT NULL"
            default_sql = f" DEFAULT {default}" if default else ""
            auto = " AUTO_INCREMENT" if name == "id" else ""
            parts.append(f"MODIFY COLUMN `{name}` {ctype} {null_sql}{default_sql}{auto} COMMENT ''")
        op.execute(f"ALTER TABLE `{table}`\n  " + ",\n  ".join(parts) + ";")

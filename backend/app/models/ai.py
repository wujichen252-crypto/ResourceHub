"""
AI 能力层 ORM 模型

包含六类数据：
1. 笔记分块与向量索引（note_chunks）—— RAG 检索底座
2. 对话与消息（ai_conversations / ai_messages）—— 多轮问答留痕
3. Agent 运行轨迹（ai_runs）—— 工具调用可回放、人在环挂起状态
4. 调用计量（ai_usage_logs）—— token 成本、成功率、限流依据
5. 提示词评测（prompt_eval_suites / cases / results）—— Prompt 实验室
6. 提示词自动优化（prompt_optimization_runs / rounds）—— 评测闭环
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class NoteChunk(Base):
    """笔记分块：RAG 的最小检索单元"""

    __tablename__ = "note_chunks"
    __table_args__ = (
        UniqueConstraint("note_id", "chunk_index", name="uq_note_chunks_note_index"),
        Index("ix_note_chunks_user_note", "user_id", "note_id"),
        {"comment": "笔记分块表：RAG 的最小检索单元，含向量索引"},
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="分块 ID，主键自增"
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户 ID（级联删除）"
    )
    note_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False, comment="所属笔记 ID（级联删除）"
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="分块序号（文内从 0 开始，与 note_id 联合唯一）"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="分块正文"
    )
    content_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="内容哈希，用于增量更新判重"
    )
    token_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="分块 token 数"
    )
    # 向量以 JSON 数组字符串存储：MySQL 5.7 无原生向量类型，万级 chunk 用 Python 余弦即可
    embedding: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="分块向量（JSON 数组字符串，MySQL 无原生向量类型）"
    )
    embedding_model: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="生成该向量的嵌入模型名"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )

    note = relationship("Note")


class AIConversation(Base):
    """AI 会话"""

    __tablename__ = "ai_conversations"
    __table_args__ = (
        Index("ix_ai_conversations_user_updated", "user_id", "updated_at"),
        {"comment": "AI 对话会话表：多轮问答的会话容器"},
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="会话 ID，主键自增"
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户 ID（级联删除）"
    )
    title: Mapped[str] = mapped_column(
        String(255), default="新对话", nullable=False, comment="会话标题，默认「新对话」"
    )
    model: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="会话使用的对话模型名，可空"
    )
    message_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="会话内消息总数"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )

    messages = relationship(
        "AIMessage", back_populates="conversation", cascade="all, delete-orphan"
    )


class AIMessage(Base):
    """AI 会话消息，检索引用与工具调用以 JSON 字符串留档"""

    __tablename__ = "ai_messages"
    __table_args__ = (
        Index("ix_ai_messages_conversation_id", "conversation_id", "id"),
        {"comment": "AI 对话消息表：检索引用与工具调用以 JSON 字符串留档"},
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="消息 ID，主键自增"
    )
    conversation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ai_conversations.id", ondelete="CASCADE"), nullable=False, comment="所属会话 ID（级联删除）"
    )
    role: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="消息角色：user=用户 / assistant=助手 / tool=工具"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="消息正文"
    )
    citations: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="检索引用来源，JSON 数组字符串，可空"
    )
    trust_json: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="回答可信度报告，JSON 对象字符串（旧消息为 NULL，前端不渲染徽章）"
    )
    tool_calls: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="工具调用记录，JSON 数组字符串，可空"
    )
    prompt_tokens: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="输入 token 数"
    )
    completion_tokens: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="输出 token 数"
    )
    latency_ms: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="响应耗时（毫秒）"
    )
    model: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="生成该消息的模型名，可空"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )

    conversation = relationship("AIConversation", back_populates="messages")


class AIRun(Base):
    """Agent 运行轨迹：steps 存完整事件序列，pending_action 存待确认写操作"""

    __tablename__ = "ai_runs"
    __table_args__ = (
        Index("ix_ai_runs_user_created", "user_id", "created_at"),
        Index("ix_ai_runs_status", "status"),
        {"comment": "Agent 运行轨迹表：完整事件序列可回放，写操作支持人在环确认"},
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="运行 ID，主键自增"
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户 ID（级联删除）"
    )
    conversation_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("ai_conversations.id", ondelete="SET NULL"), nullable=True, comment="关联会话 ID（会话删除后置空）"
    )
    goal: Mapped[str] = mapped_column(
        Text, nullable=False, comment="本次 Agent 任务目标"
    )
    status: Mapped[str] = mapped_column(
        String(20), default="running", nullable=False,
        comment="运行状态：running=执行中 / waiting_confirmation=等待人工确认 / succeeded=成功 / failed=失败 / cancelled=已取消",
    )
    steps: Mapped[str] = mapped_column(
        Text, default="[]", nullable=False, comment="执行事件序列，JSON 数组字符串（可回放）"
    )
    step_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="已执行步数"
    )
    pending_action: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="待人工确认的工具调用，JSON 字符串；确认后清除"
    )
    prompt_tokens: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="累计输入 token 数"
    )
    completion_tokens: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="累计输出 token 数"
    )
    error: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="失败原因，成功为 NULL"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="结束时间，未结束为 NULL"
    )


class AIUsageLog(Base):
    """模型调用计量：成本核算、配额限制与评测数据来源"""

    __tablename__ = "ai_usage_logs"
    __table_args__ = (
        Index("ix_ai_usage_user_created", "user_id", "created_at"),
        Index("ix_ai_usage_scene_created", "scene", "created_at"),
        {"comment": "AI 模型调用计量表：token 成本核算、配额限制与评测数据来源"},
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="日志 ID，主键自增"
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="发起调用的用户 ID（级联删除）"
    )
    scene: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="调用场景：chat=对话 / agent=智能体 / embedding=向量化 / eval=评测 / optimize=自动优化",
    )
    model: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="被调用的模型名，可空"
    )
    # 历史计量不随提示词删除而消失，故不设外键约束
    prompt_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="关联提示词 ID（eval/optimize 场景使用，用于提示词级成本归集）"
    )
    prompt_tokens: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="输入 token 数"
    )
    completion_tokens: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="输出 token 数"
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="总 token 数（输入+输出）"
    )
    latency_ms: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="调用耗时（毫秒）"
    )
    success: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="调用是否成功"
    )
    error_code: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="失败错误码，成功为 NULL"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="调用时间"
    )


class PromptEvalSuite(Base):
    """提示词评测集：一个提示词可拥有多套评测标准"""

    __tablename__ = "prompt_eval_suites"
    __table_args__ = (
        Index("ix_prompt_eval_suites_user_prompt", "user_id", "prompt_id"),
        {"comment": "提示词评测集表：一个提示词可拥有多套评测标准（Prompt 实验室）"},
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="评测集 ID，主键自增"
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户 ID（级联删除）"
    )
    prompt_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False, comment="被评测的提示词 ID（级联删除）"
    )
    name: Mapped[str] = mapped_column(
        String(191), nullable=False, comment="评测集名称"
    )
    description: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="评测集说明，可空"
    )
    judge_model: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="LLM 评委模型名，为空则用默认模型评分"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )

    cases = relationship(
        "PromptEvalCase", back_populates="suite", cascade="all, delete-orphan"
    )


class PromptEvalCase(Base):
    """单条评测用例：变量取值 + 期望输出 + 评分要点"""

    __tablename__ = "prompt_eval_cases"
    __table_args__ = (
        Index("ix_prompt_eval_cases_suite", "suite_id"),
        {"comment": "提示词评测用例表：变量取值 + 期望输出 + 评分要点"},
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="用例 ID，主键自增"
    )
    suite_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("prompt_eval_suites.id", ondelete="CASCADE"), nullable=False, comment="所属评测集 ID（级联删除）"
    )
    variables: Mapped[str] = mapped_column(
        Text, default="{}", nullable=False, comment="变量取值，JSON 对象字符串（键为提示词变量名）"
    )
    expected_output: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="期望输出（评分参考），可空"
    )
    rubric: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="评分要点，可空"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )

    suite = relationship("PromptEvalSuite", back_populates="cases")


class PromptEvalResult(Base):
    """一次评测运行的结果：按版本聚合即可做 A/B 对比"""

    __tablename__ = "prompt_eval_results"
    __table_args__ = (
        Index("ix_prompt_eval_results_suite_created", "suite_id", "created_at"),
        Index("ix_prompt_eval_results_case", "case_id"),
        {"comment": "提示词评测结果表：按版本聚合即可做 A/B 对比"},
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="结果 ID，主键自增"
    )
    suite_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("prompt_eval_suites.id", ondelete="CASCADE"), nullable=False, comment="所属评测集 ID（级联删除）"
    )
    case_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("prompt_eval_cases.id", ondelete="CASCADE"), nullable=False, comment="对应评测用例 ID（级联删除）"
    )
    prompt_version_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("prompt_versions.id", ondelete="SET NULL"), nullable=True, comment="被测提示词版本 ID（版本删除后置空）"
    )
    model: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="被测模型名，可空"
    )
    output: Mapped[str] = mapped_column(
        Text, nullable=False, comment="模型实际输出"
    )
    score: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="评委评分（0-100），未评分为 NULL"
    )
    judge_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="评委评语（扣分理由），可空"
    )
    latency_ms: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="生成耗时（毫秒）"
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="消耗总 token 数"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="评测时间"
    )


class PromptOptimizationRun(Base):
    """提示词自动优化会话：以评测结果为输入的改写-评测闭环，状态可追溯"""

    __tablename__ = "prompt_optimization_runs"
    __table_args__ = (
        Index("ix_prompt_opt_runs_user_created", "user_id", "created_at"),
        Index("ix_prompt_opt_runs_status", "status"),
        {"comment": "提示词自动优化会话表：以评测结果为输入的改写-评测闭环，状态可追溯"},
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="优化会话 ID，主键自增"
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户 ID（级联删除）"
    )
    prompt_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False, comment="被优化的提示词 ID（级联删除）"
    )
    suite_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("prompt_eval_suites.id", ondelete="CASCADE"), nullable=False, comment="优化所依据的评测集 ID（级联删除）"
    )
    status: Mapped[str] = mapped_column(
        String(20), default="running", nullable=False,
        comment="会话状态：running=优化中 / awaiting_review=等待人工采纳 / completed=已完成 / cancelled=已取消 / failed=失败",
    )
    round_number: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="当前轮次，从 0 开始"
    )
    max_rounds: Mapped[int] = mapped_column(
        Integer, default=3, nullable=False, comment="最大优化轮数，默认 3"
    )
    score_threshold: Mapped[float] = mapped_column(
        Float, default=80.0, nullable=False, comment="达标分数（达到即提前结束），默认 80"
    )
    temperature: Mapped[float] = mapped_column(
        Float, default=0.3, nullable=False, comment="改写时模型温度，默认 0.3"
    )
    # 基线：指定版本或当前正文
    baseline_version_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("prompt_versions.id", ondelete="SET NULL"), nullable=True, comment="基线版本 ID（未指定则用当前正文）"
    )
    baseline_content: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="基线正文快照"
    )
    baseline_score: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="基线评测得分（0-100）"
    )
    baseline_detail: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="基线逐用例评分明细，JSON 字符串"
    )
    # 当前轮候选
    candidate_content: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="当前轮候选正文（AI 改写结果）"
    )
    candidate_score: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="当前轮候选评测得分（0-100）"
    )
    candidate_detail: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="当前轮候选逐用例评分明细，JSON 字符串"
    )
    candidate_version_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("prompt_versions.id", ondelete="SET NULL"), nullable=True, comment="候选被采纳后保存成的版本 ID"
    )
    analysis: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="本轮 AI 诊断分析"
    )
    changelog: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="改动说明（采纳时作为版本的 commit message）"
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="整个优化会话累计消耗 token 数"
    )
    error_message: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="失败原因，成功为 NULL"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )

    rounds = relationship(
        "PromptOptimizationRound", back_populates="run", cascade="all, delete-orphan"
    )


class PromptOptimizationRound(Base):
    """自动优化的单轮历史：诊断 → 候选 → 评测 → 对比快照，供回放"""

    __tablename__ = "prompt_optimization_rounds"
    __table_args__ = (
        Index("ix_prompt_opt_rounds_run", "run_id", "round_number"),
        {"comment": "提示词自动优化轮次表：单轮历史快照（诊断→候选→评测→对比），供回放"},
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="轮次 ID，主键自增"
    )
    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("prompt_optimization_runs.id", ondelete="CASCADE"), nullable=False, comment="所属优化会话 ID（级联删除）"
    )
    round_number: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="轮次编号，会话内从 1 开始"
    )
    status: Mapped[str] = mapped_column(
        String(20), default="completed", nullable=False,
        comment="轮次状态：completed=完成 / skipped=作废（如变量漂移） / failed=失败",
    )
    candidate_content: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="本轮候选正文快照"
    )
    candidate_score: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="本轮候选评测得分（0-100）"
    )
    reference_score: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="与之对比的基准分（基线或上一轮）"
    )
    analysis: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="本轮 AI 诊断分析"
    )
    changelog: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="本轮改动说明"
    )
    snapshot: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="逐用例对比明细快照，JSON 字符串"
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="本轮消耗 token 数"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )

    run = relationship("PromptOptimizationRun", back_populates="rounds")

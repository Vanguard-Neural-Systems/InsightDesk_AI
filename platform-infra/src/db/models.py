# ──────────────────────────────────────────────────────────────────────────────
# InsightDesk AI — ORM Models
# Three core tables that form the "Memory" of the platform:
#   • interaction_log  — Full reasoning session telemetry (from AgentExecutionState)
#   • judge_verdict    — Per-judge scores from the JRH ensemble
#   • rca_trace        — Root Cause Analysis diagnostic records
#
# Schema alignment:
#   interaction_log columns are mapped 1:1 from shared.schemas.reasoning
#   judge_verdict and rca_trace are platform-infra–specific extensions.
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)

# ── JSON column helper ──────────────────────────────────────────────────────
# Use native JSONB on PostgreSQL; fall back to JSON for SQLite.
from sqlalchemy.dialects import postgresql
from sqlalchemy import JSON

# Try JSONB; if the dialect doesn't support it the column falls back to JSON.
JSONColumn = JSON().with_variant(postgresql.JSONB(), "postgresql")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


# ── Declarative Base ────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ═══════════════════════════════════════════════════════════════════════════════
#  INTERACTION LOG — "Memory" of every reasoning session
# ═══════════════════════════════════════════════════════════════════════════════

class InteractionLog(Base):
    """
    Structured record of a single agent reasoning session.

    Mapped from ``shared.schemas.reasoning.AgentExecutionState``:
      session_id, query, steps (JSONB), tool_calls (JSONB),
      memory_tier_used, final_resolution, autonomous_resolution,
      accuracy_score, hallucination_flag, total_latency_ms.
    """

    __tablename__ = "interaction_log"

    # ── Primary key ─────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── Core identity (from AgentExecutionState) ────────────────────────────
    session_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True,
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)

    # ── Reasoning chain (stored as structured JSON) ─────────────────────────
    steps: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONColumn, nullable=True, default=list,
        comment="List[ThoughtStep] serialized — step_index, thinking, action_type, confidence…",
    )
    tool_calls: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONColumn, nullable=True, default=list,
        comment="List[ToolInvocation] serialized — tool_name, arguments, result, success…",
    )

    # ── Resolution metadata ─────────────────────────────────────────────────
    memory_tier_used: Mapped[str] = mapped_column(
        String(32), default="working",
    )
    generator_provider: Mapped[str] = mapped_column(
        String(32), default="mock",
    )
    generator_model: Mapped[str] = mapped_column(
        String(64), default="deterministic",
    )
    final_resolution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    autonomous_resolution: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True,
    )

    # ── Quality signals ─────────────────────────────────────────────────────
    accuracy_score: Mapped[float] = mapped_column(
        Float, default=0.0, index=True,
        comment="Groundedness score — target ≥ 0.98",
    )
    hallucination_flag: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True,
    )
    total_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)

    # ── JRH composite score (filled after evaluation) ──────────────────────
    jrh_composite_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True,
        comment="Weighted average from the 3-judge ensemble",
    )
    jrh_needs_calibration: Mapped[bool] = mapped_column(
        Boolean, default=False,
        comment="True if judge entropy exceeded threshold",
    )

    # ── Timestamps ──────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        server_default=func.now(),
        index=True,
    )

    # ── Relationships ───────────────────────────────────────────────────────
    verdicts: Mapped[List["JudgeVerdict"]] = relationship(
        back_populates="interaction", cascade="all, delete-orphan",
    )
    rca_traces: Mapped[List["RCATrace"]] = relationship(
        back_populates="interaction", cascade="all, delete-orphan",
    )

    # ── Table-level indexes for analytics ───────────────────────────────────
    __table_args__ = (
        Index("ix_interaction_quality", "accuracy_score", "hallucination_flag"),
        Index("ix_interaction_timeline", "created_at", "autonomous_resolution"),
    )

    def __repr__(self) -> str:
        return (
            f"<InteractionLog session={self.session_id!r} "
            f"accuracy={self.accuracy_score:.2f} hallucination={self.hallucination_flag}>"
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  JUDGE VERDICT — Per-judge scores from the JRH ensemble
# ═══════════════════════════════════════════════════════════════════════════════

class JudgeVerdict(Base):
    """
    One evaluation from a single judge model.
    Each interaction gets exactly 3 verdicts (one per provider).
    """

    __tablename__ = "judge_verdict"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    interaction_id: Mapped[int] = mapped_column(
        ForeignKey("interaction_log.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Judge identity ──────────────────────────────────────────────────────
    judge_provider: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="openai | anthropic | gemini",
    )
    judge_model: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="Specific model name, e.g. gpt-4o",
    )
    position_index: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Randomized position in which this judge saw the response (0-2) — for bias mitigation",
    )

    # ── Scoring ─────────────────────────────────────────────────────────────
    score: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Judge score (0-10)",
    )
    reasoning: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Chain-of-thought reasoning from the judge",
    )
    confidence: Mapped[float] = mapped_column(
        Float, default=1.0,
        comment="Judge's self-assessed confidence (0-1)",
    )

    # ── G-Eval sub-scores (optional, filled when G-Eval is used) ───────────
    coherence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    consistency_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fluency_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    relevance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # ── Timestamps ──────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )

    # ── Relationships ───────────────────────────────────────────────────────
    interaction: Mapped["InteractionLog"] = relationship(back_populates="verdicts")

    def __repr__(self) -> str:
        return (
            f"<JudgeVerdict provider={self.judge_provider!r} "
            f"score={self.score:.1f} position={self.position_index}>"
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  RCA TRACE — Root Cause Analysis diagnostic records
# ═══════════════════════════════════════════════════════════════════════════════

class RCATrace(Base):
    """
    Diagnostic trace generated by the RCA engine for a failed interaction.
    Links back to the originating interaction for full traceability.
    """

    __tablename__ = "rca_trace"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    interaction_id: Mapped[int] = mapped_column(
        ForeignKey("interaction_log.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Failure classification ──────────────────────────────────────────────
    failure_category: Mapped[str] = mapped_column(
        String(48), nullable=False,
        comment=(
            "MALFORMED_TOOL_CALL | RETRIEVAL_FAILURE | LATENT_API_RESPONSE | "
            "HALLUCINATION | LOW_CONFIDENCE_CHAIN | VOICE_DEGRADATION"
        ),
    )

    # ── Diagnostic detail ───────────────────────────────────────────────────
    failed_step_index: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
        comment="Index of the ThoughtStep where failure was detected",
    )
    failed_tool_name: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True,
        comment="Name of the tool that failed (if applicable)",
    )
    root_cause_explanation: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Natural-language explanation of the root cause",
    )
    recommended_action: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Suggested corrective action for the self-healing loop",
    )

    # ── Shift-Left regression ───────────────────────────────────────────────
    regression_test_generated: Mapped[bool] = mapped_column(
        Boolean, default=False,
        comment="True if a regression test case was auto-generated from this trace",
    )
    regression_test_template: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONColumn, nullable=True,
        comment="Auto-generated regression test case template",
    )

    # ── Severity ────────────────────────────────────────────────────────────
    severity: Mapped[str] = mapped_column(
        String(16), default="medium",
        comment="critical | high | medium | low",
    )

    # ── Timestamps ──────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(),
    )

    # ── Relationships ───────────────────────────────────────────────────────
    interaction: Mapped["InteractionLog"] = relationship(back_populates="rca_traces")

    def __repr__(self) -> str:
        return (
            f"<RCATrace category={self.failure_category!r} "
            f"severity={self.severity!r} step={self.failed_step_index}>"
        )

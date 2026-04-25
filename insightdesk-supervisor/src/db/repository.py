# ──────────────────────────────────────────────────────────────────────────────
# InsightDesk AI — Interaction Intelligence Repository (CRUD)
# High-level data-access layer that bridges Core Intelligence telemetry
# (AgentExecutionState) to the persistent SQL store.
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import InteractionLog, JudgeVerdict, RCATrace

logger = logging.getLogger("insightdesk.infra.repository")


# ═══════════════════════════════════════════════════════════════════════════════
#  INTERACTION LOG
# ═══════════════════════════════════════════════════════════════════════════════

async def record_interaction(
    session: AsyncSession,
    *,
    session_id: str,
    query: str,
    steps: List[Dict[str, Any]] | None = None,
    tool_calls: List[Dict[str, Any]] | None = None,
    memory_tier_used: str = "working",
    generator_provider: str = "mock",
    generator_model: str = "deterministic",
    final_resolution: str | None = None,
    autonomous_resolution: bool = False,
    accuracy_score: float = 0.0,
    hallucination_flag: bool = False,
    total_latency_ms: float = 0.0,
) -> InteractionLog:
    """
    Persist a full agent reasoning session (maps from ``AgentExecutionState``).

    Returns the created ``InteractionLog`` with its database-assigned ``id``.
    """
    log = InteractionLog(
        session_id=session_id,
        query=query,
        steps=steps or [],
        tool_calls=tool_calls or [],
        memory_tier_used=memory_tier_used,
        generator_provider=generator_provider,
        generator_model=generator_model,
        final_resolution=final_resolution,
        autonomous_resolution=autonomous_resolution,
        accuracy_score=accuracy_score,
        hallucination_flag=hallucination_flag,
        total_latency_ms=total_latency_ms,
    )
    session.add(log)
    await session.flush()  # Populate log.id without committing

    logger.info(
        "Recorded interaction session=%s accuracy=%.2f hallucination=%s",
        session_id,
        accuracy_score,
        hallucination_flag,
    )
    return log


async def get_interaction_by_session(
    session: AsyncSession,
    session_id: str,
) -> InteractionLog | None:
    """Fetch a single interaction by its session ID."""
    stmt = select(InteractionLog).where(InteractionLog.session_id == session_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_interactions(
    session: AsyncSession,
    *,
    min_accuracy: float | None = None,
    max_accuracy: float | None = None,
    hallucination_only: bool = False,
    autonomous_only: bool = False,
    since: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> Sequence[InteractionLog]:
    """
    Query interactions with flexible filters.

    Useful for dashboard analytics and batch RCA analysis.
    """
    conditions = []

    if min_accuracy is not None:
        conditions.append(InteractionLog.accuracy_score >= min_accuracy)
    if max_accuracy is not None:
        conditions.append(InteractionLog.accuracy_score <= max_accuracy)
    if hallucination_only:
        conditions.append(InteractionLog.hallucination_flag.is_(True))
    if autonomous_only:
        conditions.append(InteractionLog.autonomous_resolution.is_(True))
    if since:
        conditions.append(InteractionLog.created_at >= since)

    stmt = (
        select(InteractionLog)
        .where(and_(*conditions) if conditions else True)
        .order_by(InteractionLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_low_quality_interactions(
    session: AsyncSession,
    accuracy_threshold: float = 0.98,
    limit: int = 50,
) -> Sequence[InteractionLog]:
    """
    Fetch interactions that fall below the SLA accuracy threshold
    OR have been flagged for hallucination.  Used as input for the
    RCA batch-analysis pipeline.
    """
    stmt = (
        select(InteractionLog)
        .where(
            (InteractionLog.accuracy_score < accuracy_threshold)
            | (InteractionLog.hallucination_flag.is_(True))
        )
        .order_by(InteractionLog.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def delete_all_interactions(session: AsyncSession) -> None:
    """Delete all interaction logs, verdicts, and RCA traces (Reset Test Data)."""
    from sqlalchemy import delete
    await session.execute(delete(RCATrace))
    await session.execute(delete(JudgeVerdict))
    await session.execute(delete(InteractionLog))
    await session.flush()


# ═══════════════════════════════════════════════════════════════════════════════
#  JUDGE VERDICTS
# ═══════════════════════════════════════════════════════════════════════════════

async def record_verdict(
    session: AsyncSession,
    *,
    interaction_id: int,
    judge_provider: str,
    judge_model: str,
    position_index: int,
    score: float,
    reasoning: str,
    confidence: float = 1.0,
    coherence_score: float | None = None,
    consistency_score: float | None = None,
    fluency_score: float | None = None,
    relevance_score: float | None = None,
) -> JudgeVerdict:
    """Persist a single judge's evaluation for an interaction."""
    verdict = JudgeVerdict(
        interaction_id=interaction_id,
        judge_provider=judge_provider,
        judge_model=judge_model,
        position_index=position_index,
        score=score,
        reasoning=reasoning,
        confidence=confidence,
        coherence_score=coherence_score,
        consistency_score=consistency_score,
        fluency_score=fluency_score,
        relevance_score=relevance_score,
    )
    session.add(verdict)
    await session.flush()

    logger.info(
        "Recorded verdict provider=%s score=%.1f for interaction_id=%d",
        judge_provider,
        score,
        interaction_id,
    )
    return verdict


async def get_verdicts_for_interaction(
    session: AsyncSession,
    interaction_id: int,
) -> Sequence[JudgeVerdict]:
    """Fetch all judge verdicts for a given interaction."""
    stmt = (
        select(JudgeVerdict)
        .where(JudgeVerdict.interaction_id == interaction_id)
        .order_by(JudgeVerdict.position_index)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def update_jrh_composite(
    session: AsyncSession,
    interaction_id: int,
    composite_score: float,
    needs_calibration: bool,
) -> None:
    """Update the JRH composite score on the parent interaction."""
    stmt = select(InteractionLog).where(InteractionLog.id == interaction_id)
    result = await session.execute(stmt)
    interaction = result.scalar_one_or_none()
    if interaction:
        interaction.jrh_composite_score = composite_score
        interaction.jrh_needs_calibration = needs_calibration
        await session.flush()


# ═══════════════════════════════════════════════════════════════════════════════
#  RCA TRACES
# ═══════════════════════════════════════════════════════════════════════════════

async def record_rca_trace(
    session: AsyncSession,
    *,
    interaction_id: int,
    failure_category: str,
    root_cause_explanation: str,
    failed_step_index: int | None = None,
    failed_tool_name: str | None = None,
    recommended_action: str | None = None,
    regression_test_generated: bool = False,
    regression_test_template: Dict[str, Any] | None = None,
    severity: str = "medium",
) -> RCATrace:
    """Persist a Root Cause Analysis diagnostic trace."""
    trace = RCATrace(
        interaction_id=interaction_id,
        failure_category=failure_category,
        root_cause_explanation=root_cause_explanation,
        failed_step_index=failed_step_index,
        failed_tool_name=failed_tool_name,
        recommended_action=recommended_action,
        regression_test_generated=regression_test_generated,
        regression_test_template=regression_test_template,
        severity=severity,
    )
    session.add(trace)
    await session.flush()

    logger.info(
        "Recorded RCA trace category=%s severity=%s for interaction_id=%d",
        failure_category,
        severity,
        interaction_id,
    )
    return trace


async def list_rca_traces(
    session: AsyncSession,
    *,
    failure_category: str | None = None,
    severity: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> Sequence[RCATrace]:
    """Query RCA traces with optional filters."""
    conditions = []
    if failure_category:
        conditions.append(RCATrace.failure_category == failure_category)
    if severity:
        conditions.append(RCATrace.severity == severity)

    from sqlalchemy.orm import selectinload

    stmt = (
        select(RCATrace)
        .options(selectinload(RCATrace.interaction))
        .where(and_(*conditions) if conditions else True)
        .order_by(RCATrace.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


# ═══════════════════════════════════════════════════════════════════════════════
#  AGGREGATE QUERIES (for dashboard metrics)
# ═══════════════════════════════════════════════════════════════════════════════

async def get_aggregate_stats(
    session: AsyncSession,
    since: datetime | None = None,
) -> Dict[str, Any]:
    """
    Compute aggregate statistics for the metrics dashboard.

    Returns:
        total_interactions, autonomous_count, hallucination_count,
        avg_accuracy, avg_latency_ms, jrh_calibration_count.
    """
    conditions = []
    if since:
        conditions.append(InteractionLog.created_at >= since)

    base_filter = and_(*conditions) if conditions else True

    # Total interactions
    total_stmt = select(
        InteractionLog.id
    ).where(base_filter)
    total_result = await session.execute(total_stmt)
    total = len(total_result.all())

    if total == 0:
        return {
            "total_interactions": 0,
            "autonomous_count": 0,
            "resolution_rate": 0.0,
            "hallucination_count": 0,
            "hallucination_index": 0.0,
            "avg_accuracy": 0.0,
            "avg_latency_ms": 0.0,
            "jrh_calibration_count": 0,
            "jrh_agreement_rate": 0.0,
        }

    # Fetch all matching interactions for in-memory aggregation
    stmt = select(InteractionLog).where(base_filter)
    result = await session.execute(stmt)
    interactions: Sequence[InteractionLog] = result.scalars().all()

    autonomous_count = sum(1 for i in interactions if i.autonomous_resolution)
    hallucination_count = sum(1 for i in interactions if i.hallucination_flag)
    jrh_calibration_count = sum(1 for i in interactions if i.jrh_needs_calibration)
    avg_accuracy = sum(i.accuracy_score for i in interactions) / total
    avg_latency = sum(i.total_latency_ms for i in interactions) / total

    scored_interactions = [i for i in interactions if i.jrh_composite_score is not None]
    jrh_agreement_rate = (
        sum(1 for i in scored_interactions if not i.jrh_needs_calibration)
        / len(scored_interactions)
        if scored_interactions
        else 0.0
    )

    return {
        "total_interactions": total,
        "autonomous_count": autonomous_count,
        "resolution_rate": round(autonomous_count / total, 4),
        "hallucination_count": hallucination_count,
        "hallucination_index": round(hallucination_count / total, 4),
        "avg_accuracy": round(avg_accuracy, 4),
        "avg_latency_ms": round(avg_latency, 2),
        "jrh_calibration_count": jrh_calibration_count,
        "jrh_agreement_rate": round(jrh_agreement_rate, 4),
    }

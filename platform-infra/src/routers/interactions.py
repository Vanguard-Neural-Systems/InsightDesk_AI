# ──────────────────────────────────────────────────────────────────────────────
# InsightDesk AI — Interactions Router
# /interactions/* endpoints for ingesting and querying agent telemetry.
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.engine import get_async_session
from src.db import repository

logger = logging.getLogger("insightdesk.infra.router.interactions")

router = APIRouter(prefix="/interactions", tags=["Interactions"])


# ── Request / Response Models ───────────────────────────────────────────────

class IngestRequest(BaseModel):
    """Maps from shared.schemas.reasoning.AgentExecutionState."""
    session_id: str
    query: str
    steps: List[Dict[str, Any]] = Field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    memory_tier_used: str = "working"
    generator_provider: str = "mock"
    generator_model: str = "deterministic"
    final_resolution: Optional[str] = None
    autonomous_resolution: bool = False
    accuracy_score: float = 0.0
    hallucination_flag: bool = False
    total_latency_ms: float = 0.0


class InteractionResponse(BaseModel):
    id: int
    session_id: str
    query: str
    accuracy_score: float
    hallucination_flag: bool
    autonomous_resolution: bool
    total_latency_ms: float
    jrh_composite_score: Optional[float] = None
    jrh_needs_calibration: bool = False
    created_at: Optional[datetime] = None


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.post(
    "/ingest",
    response_model=InteractionResponse,
    summary="Ingest an AgentExecutionState from Core Intelligence",
)
async def ingest_interaction(
    req: IngestRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Accept a full agent reasoning session telemetry payload and persist
    it to the Interaction Intelligence Repository.
    """
    log = await repository.record_interaction(
        session,
        session_id=req.session_id,
        query=req.query,
        steps=req.steps,
        tool_calls=req.tool_calls,
        memory_tier_used=req.memory_tier_used,
        generator_provider=req.generator_provider,
        generator_model=req.generator_model,
        final_resolution=req.final_resolution,
        autonomous_resolution=req.autonomous_resolution,
        accuracy_score=req.accuracy_score,
        hallucination_flag=req.hallucination_flag,
        total_latency_ms=req.total_latency_ms,
    )
    return InteractionResponse(
        id=log.id,
        session_id=log.session_id,
        query=log.query,
        accuracy_score=log.accuracy_score,
        hallucination_flag=log.hallucination_flag,
        autonomous_resolution=log.autonomous_resolution,
        total_latency_ms=log.total_latency_ms,
        jrh_composite_score=log.jrh_composite_score,
        jrh_needs_calibration=log.jrh_needs_calibration,
        created_at=log.created_at,
    )


@router.get(
    "/",
    response_model=List[InteractionResponse],
    summary="List interactions with filters",
)
async def list_interactions(
    min_accuracy: Optional[float] = Query(None, ge=0, le=1),
    max_accuracy: Optional[float] = Query(None, ge=0, le=1),
    hallucination_only: bool = Query(False),
    autonomous_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_async_session),
):
    """Query interactions with flexible filters for analytics."""
    interactions = await repository.list_interactions(
        session,
        min_accuracy=min_accuracy,
        max_accuracy=max_accuracy,
        hallucination_only=hallucination_only,
        autonomous_only=autonomous_only,
        limit=limit,
        offset=offset,
    )
    return [
        InteractionResponse(
            id=i.id,
            session_id=i.session_id,
            query=i.query,
            accuracy_score=i.accuracy_score,
            hallucination_flag=i.hallucination_flag,
            autonomous_resolution=i.autonomous_resolution,
            total_latency_ms=i.total_latency_ms,
            jrh_composite_score=i.jrh_composite_score,
            jrh_needs_calibration=i.jrh_needs_calibration,
            created_at=i.created_at,
        )
        for i in interactions
    ]


@router.get(
    "/{session_id}",
    summary="Get a single interaction with verdicts and RCA traces",
)
async def get_interaction(
    session_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Fetch a full interaction record with all judge verdicts and RCA traces."""
    interaction = await repository.get_interaction_by_session(session, session_id)
    if not interaction:
        raise HTTPException(404, f"Interaction '{session_id}' not found")

    verdicts = await repository.get_verdicts_for_interaction(session, interaction.id)

    return {
        "interaction": {
            "id": interaction.id,
            "session_id": interaction.session_id,
            "query": interaction.query,
            "steps": interaction.steps,
            "tool_calls": interaction.tool_calls,
            "memory_tier_used": interaction.memory_tier_used,
            "final_resolution": interaction.final_resolution,
            "autonomous_resolution": interaction.autonomous_resolution,
            "accuracy_score": interaction.accuracy_score,
            "hallucination_flag": interaction.hallucination_flag,
            "total_latency_ms": interaction.total_latency_ms,
            "jrh_composite_score": interaction.jrh_composite_score,
            "jrh_needs_calibration": interaction.jrh_needs_calibration,
            "created_at": interaction.created_at.isoformat() if interaction.created_at else None,
        },
        "verdicts": [
            {
                "judge_provider": v.judge_provider,
                "judge_model": v.judge_model,
                "score": v.score,
                "reasoning": v.reasoning,
                "confidence": v.confidence,
                "position_index": v.position_index,
                "coherence_score": v.coherence_score,
                "consistency_score": v.consistency_score,
                "fluency_score": v.fluency_score,
                "relevance_score": v.relevance_score,
            }
            for v in verdicts
        ],
    }

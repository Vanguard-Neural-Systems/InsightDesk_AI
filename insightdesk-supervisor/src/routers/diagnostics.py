# ──────────────────────────────────────────────────────────────────────────────
# InsightDesk AI — Diagnostics Router
# /diagnostics/* endpoints for Root Cause Analysis.
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.db.engine import get_async_session
from src.db import repository
from src.diagnostics.rca_engine import RCAEngine

logger = logging.getLogger("insightdesk.infra.router.diagnostics")

router = APIRouter(prefix="/diagnostics", tags=["Diagnostics"])

_rca: Optional[RCAEngine] = None


def init_diagnostics(rca: RCAEngine) -> None:
    """Called during app startup."""
    global _rca
    _rca = rca


class AnalyzeRequest(BaseModel):
    session_id: str = Field(..., description="Session ID to analyze")


@router.post("/analyze", summary="Run RCA on a specific interaction")
async def analyze_interaction(
    req: AnalyzeRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Perform Root Cause Analysis on a stored interaction.
    Classifies failures, generates NL explanation, and creates
    a shift-left regression test template.
    """
    if not _rca:
        raise HTTPException(503, "RCA engine not initialized")

    interaction = await repository.get_interaction_by_session(session, req.session_id)
    if not interaction:
        raise HTTPException(404, f"Interaction '{req.session_id}' not found")

    diagnostic = _rca.analyze(
        session_id=interaction.session_id,
        query=interaction.query,
        steps=interaction.steps or [],
        tool_calls=interaction.tool_calls or [],
        final_resolution=interaction.final_resolution,
        accuracy_score=interaction.accuracy_score,
        hallucination_flag=interaction.hallucination_flag,
        total_latency_ms=interaction.total_latency_ms,
    )

    # Persist the trace
    if diagnostic.findings:
        await repository.record_rca_trace(
            session,
            interaction_id=interaction.id,
            failure_category=diagnostic.primary_category,
            root_cause_explanation=diagnostic.root_cause_explanation,
            failed_step_index=diagnostic.failed_step_index,
            failed_tool_name=diagnostic.failed_tool_name,
            recommended_action=diagnostic.recommended_action,
            regression_test_generated=diagnostic.regression_test_template is not None,
            regression_test_template=diagnostic.regression_test_template,
            severity=diagnostic.primary_severity,
        )

    return diagnostic.to_dict()


@router.get("/traces", summary="List all RCA traces with filters")
async def list_traces(
    failure_category: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_async_session),
):
    """Query RCA traces with optional category and severity filters."""
    traces = await repository.list_rca_traces(
        session,
        failure_category=failure_category,
        severity=severity,
        limit=limit,
        offset=offset,
    )
    return [
        {
            "id": t.id,
            "interaction_id": t.interaction_id,
            "session_id": t.interaction.session_id if t.interaction else None,
            "failure_category": t.failure_category,
            "severity": t.severity,
            "failed_step_index": t.failed_step_index,
            "failed_tool_name": t.failed_tool_name,
            "root_cause_explanation": t.root_cause_explanation,
            "recommended_action": t.recommended_action,
            "regression_test_generated": t.regression_test_generated,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in traces
    ]


@router.post("/batch-analyze", summary="Batch-analyze all low-quality interactions")
async def batch_analyze(
    accuracy_threshold: float = Query(default=0.98, ge=0, le=1),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Fetch all interactions below the accuracy SLA or flagged for hallucination,
    and run RCA on each. Returns a summary of diagnostics.
    """
    if not _rca:
        raise HTTPException(503, "RCA engine not initialized")

    low_quality = await repository.get_low_quality_interactions(
        session, accuracy_threshold=accuracy_threshold, limit=limit,
    )

    results = []
    for interaction in low_quality:
        diagnostic = _rca.analyze(
            session_id=interaction.session_id,
            query=interaction.query,
            steps=interaction.steps or [],
            tool_calls=interaction.tool_calls or [],
            final_resolution=interaction.final_resolution,
            accuracy_score=interaction.accuracy_score,
            hallucination_flag=interaction.hallucination_flag,
            total_latency_ms=interaction.total_latency_ms,
        )

        if diagnostic.findings:
            await repository.record_rca_trace(
                session,
                interaction_id=interaction.id,
                failure_category=diagnostic.primary_category,
                root_cause_explanation=diagnostic.root_cause_explanation,
                failed_step_index=diagnostic.failed_step_index,
                failed_tool_name=diagnostic.failed_tool_name,
                recommended_action=diagnostic.recommended_action,
                regression_test_generated=diagnostic.regression_test_template is not None,
                regression_test_template=diagnostic.regression_test_template,
                severity=diagnostic.primary_severity,
            )

        results.append(diagnostic.to_dict())

    return {
        "analyzed_count": len(results),
        "threshold": accuracy_threshold,
        "diagnostics": results,
    }

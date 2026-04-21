# ──────────────────────────────────────────────────────────────────────────────
# InsightDesk AI — Evaluation Router
# /evaluate/* endpoints for JRH ensemble and G-Eval assessments.
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.engine import get_async_session
from src.db import repository
from src.evaluators.jrh_ensemble import JRHEnsemble, EnsembleResult
from src.evaluators.g_eval import GEvaluator

logger = logging.getLogger("insightdesk.infra.router.evaluation")

router = APIRouter(prefix="/evaluate", tags=["Evaluation"])

# Module-level singletons (initialized by main.py lifespan)
_jrh: Optional[JRHEnsemble] = None
_g_eval: Optional[GEvaluator] = None


def init_evaluators(jrh: JRHEnsemble, g_eval: GEvaluator) -> None:
    """Called during app startup to inject evaluator instances."""
    global _jrh, _g_eval
    _jrh = jrh
    _g_eval = g_eval


# ── Request Models ──────────────────────────────────────────────────────────

class EvalBySessionRequest(BaseModel):
    session_id: str = Field(..., description="Session ID of the interaction to evaluate")


class EvalDirectRequest(BaseModel):
    """Direct evaluation without requiring a stored interaction."""
    query: str
    thought_chain: List[Dict[str, Any]] = Field(default_factory=list)
    final_resolution: str = ""
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    generator_provider: str = "mock"


# ── JRH Endpoints ──────────────────────────────────────────────────────────

@router.post("/jrh", summary="Run JRH ensemble on a stored interaction")
async def evaluate_jrh_by_session(
    req: EvalBySessionRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Run the full 3-judge JRH evaluation on a stored interaction.
    Stores verdicts in the database and updates the composite score.
    """
    if not _jrh:
        raise HTTPException(503, "JRH ensemble not initialized")

    interaction = await repository.get_interaction_by_session(session, req.session_id)
    if not interaction:
        raise HTTPException(404, f"Interaction '{req.session_id}' not found")

    result: EnsembleResult = await _jrh.evaluate(
        query=interaction.query,
        thought_chain=interaction.steps or [],
        final_resolution=interaction.final_resolution or "",
        tool_calls=interaction.tool_calls or [],
        generator_provider=interaction.generator_provider,
    )

    # Persist each judge's verdict
    for idx, score in enumerate(result.judge_scores):
        await repository.record_verdict(
            session,
            interaction_id=interaction.id,
            judge_provider=score.provider,
            judge_model=score.model,
            position_index=idx,
            score=score.score,
            reasoning=score.reasoning,
            confidence=score.confidence,
            coherence_score=score.coherence,
            consistency_score=score.consistency,
            fluency_score=score.fluency,
            relevance_score=score.relevance,
        )

    # Update composite score on the interaction
    await repository.update_jrh_composite(
        session,
        interaction_id=interaction.id,
        composite_score=result.composite_score,
        needs_calibration=result.needs_human_calibration,
    )

    return result.to_dict()


@router.post("/jrh/direct", summary="Run JRH ensemble on raw input (no DB lookup)")
async def evaluate_jrh_direct(req: EvalDirectRequest):
    """Run JRH evaluation on provided data without requiring a stored interaction."""
    if not _jrh:
        raise HTTPException(503, "JRH ensemble not initialized")

    result = await _jrh.evaluate(
        query=req.query,
        thought_chain=req.thought_chain,
        final_resolution=req.final_resolution,
        tool_calls=req.tool_calls,
        generator_provider=req.generator_provider,
    )
    return result.to_dict()


# ── G-Eval Endpoints ───────────────────────────────────────────────────────

@router.post("/g-eval", summary="Run G-Eval with CoT on a stored interaction")
async def evaluate_geval_by_session(
    req: EvalBySessionRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Run G-Eval assessment with Chain-of-Thought on a stored interaction."""
    if not _g_eval:
        raise HTTPException(503, "G-Eval evaluator not initialized")

    interaction = await repository.get_interaction_by_session(session, req.session_id)
    if not interaction:
        raise HTTPException(404, f"Interaction '{req.session_id}' not found")

    result = await _g_eval.evaluate(
        query=interaction.query,
        thought_chain=interaction.steps or [],
        final_resolution=interaction.final_resolution or "",
        tool_calls=interaction.tool_calls or [],
    )
    return result.to_dict()


# ── Verdict Retrieval ──────────────────────────────────────────────────────

@router.get(
    "/verdicts/{session_id}",
    summary="Get all judge verdicts for a session",
)
async def get_verdicts(
    session_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve all JRH judge verdicts for a given interaction session."""
    interaction = await repository.get_interaction_by_session(session, session_id)
    if not interaction:
        raise HTTPException(404, f"Interaction '{session_id}' not found")

    verdicts = await repository.get_verdicts_for_interaction(session, interaction.id)
    return {
        "session_id": session_id,
        "composite_score": interaction.jrh_composite_score,
        "needs_calibration": interaction.jrh_needs_calibration,
        "verdicts": [
            {
                "judge_provider": v.judge_provider,
                "judge_model": v.judge_model,
                "score": v.score,
                "reasoning": v.reasoning,
                "confidence": v.confidence,
                "position_index": v.position_index,
            }
            for v in verdicts
        ],
    }

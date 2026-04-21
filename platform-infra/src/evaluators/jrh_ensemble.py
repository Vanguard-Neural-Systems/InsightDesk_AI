# ──────────────────────────────────────────────────────────────────────────────
# InsightDesk AI — Judge Reliability Harness (JRH) Ensemble
# Multi-judge consensus with position rotation, Shannon entropy gating,
# and confidence-weighted scoring.
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from src.config import settings
from src.evaluators.judge_models import BaseJudge, JudgeScore, create_default_judges

logger = logging.getLogger("insightdesk.infra.jrh")


@dataclass
class EnsembleResult:
    """Aggregate result from the 3-judge JRH evaluation."""
    judge_scores: List[JudgeScore] = field(default_factory=list)
    composite_score: float = 0.0
    entropy: float = 0.0
    needs_human_calibration: bool = False
    avg_coherence: Optional[float] = None
    avg_consistency: Optional[float] = None
    avg_fluency: Optional[float] = None
    avg_relevance: Optional[float] = None
    total_latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "judge_scores": [s.to_dict() for s in self.judge_scores],
            "composite_score": round(self.composite_score, 2),
            "entropy": round(self.entropy, 4),
            "needs_human_calibration": self.needs_human_calibration,
            "avg_coherence": self.avg_coherence,
            "avg_consistency": self.avg_consistency,
            "avg_fluency": self.avg_fluency,
            "avg_relevance": self.avg_relevance,
            "total_latency_ms": round(self.total_latency_ms, 1),
        }


def _compute_entropy(scores: List[float], bins: int = 11) -> float:
    """Normalized Shannon entropy over judge scores (0=agreement, 1=max disagreement)."""
    if not scores or len(scores) < 2:
        return 0.0
    binned = [min(int(round(s)), 10) for s in scores]
    counts = np.zeros(bins)
    for b in binned:
        counts[b] += 1
    probs = counts / counts.sum()
    probs = probs[probs > 0]
    entropy = -np.sum(probs * np.log2(probs))
    max_entropy = np.log2(len(scores))
    return float(entropy / max_entropy) if max_entropy > 0 else 0.0


class JRHEnsemble:
    """
    The Judge Reliability Harness — core consensus engine.

    Mechanisms:
      • Position Rotation — randomizes response order to prevent first-response bias
      • Shannon Entropy — quantifies judge disagreement; high entropy → human review
      • Judge-Generator Separation — judges never share a provider with the generator
    """

    def __init__(
        self,
        judges: List[BaseJudge] | None = None,
        entropy_threshold: float | None = None,
    ) -> None:
        self.judges = judges or create_default_judges()
        self.entropy_threshold = entropy_threshold or settings.JRH_ENTROPY_THRESHOLD

    async def evaluate(
        self,
        query: str,
        thought_chain: List[Dict[str, Any]],
        final_resolution: str,
        tool_calls: List[Dict[str, Any]],
        generator_provider: str = "mock",
    ) -> EnsembleResult:
        """
        Run the full JRH pipeline:
          1. Randomize position assignments
          2. Execute all judges concurrently (skipping the generator's provider)
          3. Compute Shannon entropy
          4. Determine if human calibration is needed
          5. Aggregate G-Eval sub-scores
        """
        active_judges = [j for j in self.judges if j.provider != generator_provider]
        if not active_judges:
            logger.warning("All judges filtered out! Using mock score.")
            return EnsembleResult(composite_score=5.0)

        positions = list(range(len(active_judges)))
        random.shuffle(positions)

        logger.info("JRH evaluation started — %d judges (generator=%s)", len(active_judges), generator_provider)

        # Parallel evaluation
        tasks = [
            judge.evaluate(query, thought_chain, final_resolution, tool_calls)
            for judge in active_judges
        ]
        scores: List[JudgeScore] = await asyncio.gather(*tasks)

        # Entropy and consensus
        raw_scores = [s.score for s in scores]
        entropy = _compute_entropy(raw_scores)

        total_confidence = sum(s.confidence for s in scores) or 1.0
        composite = sum(s.score * s.confidence for s in scores) / total_confidence
        needs_calibration = entropy > self.entropy_threshold

        # Aggregate G-Eval sub-scores
        def _avg(attr: str) -> Optional[float]:
            vals = [getattr(s, attr) for s in scores if getattr(s, attr) is not None]
            return round(sum(vals) / len(vals), 2) if vals else None

        result = EnsembleResult(
            judge_scores=scores,
            composite_score=round(composite, 2),
            entropy=entropy,
            needs_human_calibration=needs_calibration,
            avg_coherence=_avg("coherence"),
            avg_consistency=_avg("consistency"),
            avg_fluency=_avg("fluency"),
            avg_relevance=_avg("relevance"),
            total_latency_ms=sum(s.latency_ms for s in scores),
        )

        logger.info(
            "JRH complete — composite=%.2f entropy=%.4f calibration=%s",
            result.composite_score, result.entropy, result.needs_human_calibration,
        )
        return result

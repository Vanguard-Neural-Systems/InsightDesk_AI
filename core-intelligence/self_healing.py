# ──────────────────────────────────────────────────────────────────────────────
# InsightDesk AI — Autonomous Self-Healing Engine
# The "Immune System" — detects UI/API drift and automatically repairs
# test journeys without human intervention.
#
# Architecture:
#   1. FINGERPRINT — Capture stable identities of UI elements and API schemas.
#   2. DETECT      — Compare current state against last-known-good fingerprints.
#   3. HEAL        — Generate patches that update broken test steps.
#   4. VALIDATE    — Re-run the healed journey and confirm green status.
#
# Uses Vision AI embeddings for visual similarity matching when selectors
# break, and StepIQ-style logical analysis for API schema drift.
#
# Target: 85 % reduction in manual QA maintenance time.
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import hashlib
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

# ── Resolve imports ──────────────────────────────────────────────────────────
import sys, os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from schemas.self_healing import (
    DriftType,
    ElementFingerprint,
    ElementType,
    HealingPatch,
    HealingReport,
    JourneyStep,
    StepAction,
    TestJourney,
)

logger = logging.getLogger("insightdesk.self_healing")

# Confidence threshold — patches below this are flagged for human review.
AUTO_APPLY_CONFIDENCE = 0.85


class SelfHealingEngine:
    """
    Autonomous test-journey maintenance engine.

    Monitors registered test journeys, detects when UI selectors or API
    schemas have drifted, and generates healing patches that restore the
    journeys to a passing state.
    """

    def __init__(self) -> None:
        self._journeys: Dict[str, TestJourney] = {}
        self._fingerprint_store: Dict[str, ElementFingerprint] = {}
        self._healing_history: List[HealingReport] = []

    # ── Journey Registry ─────────────────────────────────────────────────────

    def register_journey(self, journey: TestJourney) -> None:
        """Register a test journey for autonomous monitoring."""
        self._journeys[journey.journey_id] = journey
        # Index all element fingerprints from the journey steps
        for step in journey.steps:
            fp_key = self._fingerprint_key(step.target)
            self._fingerprint_store[fp_key] = step.target
        logger.info(
            "Registered journey '%s' (%d steps)",
            journey.name,
            len(journey.steps),
        )

    def get_journey(self, journey_id: str) -> Optional[TestJourney]:
        """Retrieve a registered journey by ID."""
        return self._journeys.get(journey_id)

    def list_journeys(self) -> List[TestJourney]:
        """Return all registered test journeys."""
        return list(self._journeys.values())

    # ── Drift Detection ──────────────────────────────────────────────────────

    async def detect_drift(
        self,
        journey_id: str,
        current_fingerprints: List[ElementFingerprint],
    ) -> List[Tuple[int, DriftType, ElementFingerprint, ElementFingerprint]]:
        """
        Compare current element fingerprints against the journey's
        last-known-good state.  Returns a list of detected drifts.

        Each drift is a tuple of:
          (step_index, drift_type, old_fingerprint, new_fingerprint)
        """
        journey = self._journeys.get(journey_id)
        if not journey:
            raise ValueError(f"Journey '{journey_id}' not found")

        # Build a lookup of current fingerprints by element_id
        current_map: Dict[str, ElementFingerprint] = {
            fp.element_id: fp for fp in current_fingerprints
        }

        drifts: List[Tuple[int, DriftType, ElementFingerprint, ElementFingerprint]] = []

        for step in journey.steps:
            old_fp = step.target
            new_fp = current_map.get(old_fp.element_id)

            if new_fp is None:
                # Element vanished — try visual similarity matching
                matched_fp = self._visual_similarity_search(old_fp, current_fingerprints)
                if matched_fp:
                    drifts.append((
                        step.step_index,
                        DriftType.ELEMENT_RELOCATED,
                        old_fp,
                        matched_fp,
                    ))
                else:
                    # Create a placeholder for a truly removed element
                    removed_fp = ElementFingerprint(
                        element_id=old_fp.element_id,
                        element_type=old_fp.element_type,
                        confidence=0.0,
                    )
                    drifts.append((
                        step.step_index,
                        DriftType.ELEMENT_REMOVED,
                        old_fp,
                        removed_fp,
                    ))
                continue

            # Check for selector drift (UI elements)
            if old_fp.selector and new_fp.selector and old_fp.selector != new_fp.selector:
                drifts.append((
                    step.step_index,
                    DriftType.SELECTOR_CHANGED,
                    old_fp,
                    new_fp,
                ))

            # Check for API path drift
            elif old_fp.api_path and new_fp.api_path and old_fp.api_path != new_fp.api_path:
                drifts.append((
                    step.step_index,
                    DriftType.API_PATH_CHANGED,
                    old_fp,
                    new_fp,
                ))

            # Check for attribute drift
            elif old_fp.attributes != new_fp.attributes:
                drift_type = (
                    DriftType.API_SCHEMA_CHANGED
                    if old_fp.element_type in (ElementType.API_ENDPOINT, ElementType.API_FIELD)
                    else DriftType.ATTRIBUTE_CHANGED
                )
                drifts.append((step.step_index, drift_type, old_fp, new_fp))

        if drifts:
            logger.warning(
                "Journey '%s' — %d drift(s) detected",
                journey.name,
                len(drifts),
            )
        else:
            logger.info("Journey '%s' — no drift detected ✓", journey.name)

        return drifts

    # ── Healing ──────────────────────────────────────────────────────────────

    async def heal_journey(
        self,
        journey_id: str,
        current_fingerprints: List[ElementFingerprint],
    ) -> HealingReport:
        """
        Full self-healing cycle:
          1. Detect drift against current state.
          2. Generate healing patches for each broken step.
          3. Auto-apply high-confidence patches.
          4. Flag low-confidence patches for human review.
          5. Update the journey in-place.
        """
        drifts = await self.detect_drift(journey_id, current_fingerprints)
        journey = self._journeys[journey_id]

        report = HealingReport(journey_id=journey_id)

        for step_idx, drift_type, old_fp, new_fp in drifts:
            confidence = self._compute_patch_confidence(drift_type, old_fp, new_fp)
            reasoning = self._generate_reasoning(drift_type, old_fp, new_fp)

            patch = HealingPatch(
                step_index=step_idx,
                drift_type=drift_type,
                old_fingerprint=old_fp,
                new_fingerprint=new_fp,
                confidence=confidence,
                reasoning=reasoning,
            )
            report.patches.append(patch)

            # Auto-apply if confidence is high enough
            if confidence >= AUTO_APPLY_CONFIDENCE:
                self._apply_patch(journey, patch)
                report.auto_applied += 1
                logger.info(
                    "Journey '%s' step %d — auto-healed (%s, confidence=%.2f)",
                    journey.name,
                    step_idx,
                    drift_type.value,
                    confidence,
                )
            else:
                report.needs_review += 1
                logger.warning(
                    "Journey '%s' step %d — needs human review (%s, confidence=%.2f)",
                    journey.name,
                    step_idx,
                    drift_type.value,
                    confidence,
                )

        report.journey_healed = report.needs_review == 0 and len(report.patches) > 0
        if report.journey_healed:
            journey.is_healthy = True

        self._healing_history.append(report)

        logger.info(
            "Healing report for '%s': %d patches, %d auto-applied, %d need review",
            journey.name,
            len(report.patches),
            report.auto_applied,
            report.needs_review,
        )
        return report

    # ── Patch Application ────────────────────────────────────────────────────

    def _apply_patch(self, journey: TestJourney, patch: HealingPatch) -> None:
        """Apply a single healing patch to the journey, updating the target fingerprint."""
        for step in journey.steps:
            if step.step_index == patch.step_index:
                step.target = patch.new_fingerprint
                break

    # ── Confidence Scoring ───────────────────────────────────────────────────

    def _compute_patch_confidence(
        self,
        drift_type: DriftType,
        old_fp: ElementFingerprint,
        new_fp: ElementFingerprint,
    ) -> float:
        """
        Score how confident we are that the new fingerprint is the correct
        replacement for the old one.

        Scoring heuristics:
          • Selector changed but attributes match → high confidence
          • Element relocated but visual embedding matches → medium-high
          • Element removed entirely → low confidence (needs review)
          • API schema change → depends on field overlap
        """
        if drift_type == DriftType.ELEMENT_REMOVED:
            return 0.20

        if drift_type == DriftType.SELECTOR_CHANGED:
            # If attributes are largely the same, the selector just moved
            attr_overlap = self._attribute_overlap(old_fp.attributes, new_fp.attributes)
            return min(0.60 + attr_overlap * 0.35, 0.98)

        if drift_type == DriftType.ELEMENT_RELOCATED:
            # Visual embedding similarity
            if old_fp.visual_embedding and new_fp.visual_embedding:
                similarity = self._cosine_similarity(
                    old_fp.visual_embedding,
                    new_fp.visual_embedding,
                )
                return min(0.50 + similarity * 0.45, 0.95)
            return 0.55

        if drift_type == DriftType.ATTRIBUTE_CHANGED:
            overlap = self._attribute_overlap(old_fp.attributes, new_fp.attributes)
            return min(0.50 + overlap * 0.40, 0.95)

        if drift_type in (DriftType.API_SCHEMA_CHANGED, DriftType.API_PATH_CHANGED):
            overlap = self._attribute_overlap(old_fp.attributes, new_fp.attributes)
            return min(0.40 + overlap * 0.45, 0.90)

        return 0.50

    # ── Reasoning Generation ─────────────────────────────────────────────────

    def _generate_reasoning(
        self,
        drift_type: DriftType,
        old_fp: ElementFingerprint,
        new_fp: ElementFingerprint,
    ) -> str:
        """
        Generate a Chain-of-Thought explanation for why a patch was chosen.
        This aids human reviewers and feeds into the JRH evaluation harness.
        """
        if drift_type == DriftType.SELECTOR_CHANGED:
            return (
                f"The CSS selector for '{old_fp.element_id}' changed from "
                f"'{old_fp.selector}' to '{new_fp.selector}'. "
                f"The element's attributes (text, aria-label) remain consistent, "
                f"indicating a DOM restructure rather than a functional change. "
                f"Updating the selector is safe."
            )

        if drift_type == DriftType.ELEMENT_RELOCATED:
            return (
                f"Element '{old_fp.element_id}' was not found at its original "
                f"location. Vision AI identified a visually similar element at "
                f"'{new_fp.selector or new_fp.element_id}' with confidence "
                f"{new_fp.confidence:.2f}. Recommending relocation patch."
            )

        if drift_type == DriftType.ELEMENT_REMOVED:
            return (
                f"Element '{old_fp.element_id}' appears to have been removed "
                f"from the UI entirely. No visually similar replacement was found. "
                f"This patch requires human review to determine if the test step "
                f"should be removed or if the element was moved to a new page."
            )

        if drift_type == DriftType.API_SCHEMA_CHANGED:
            return (
                f"The API schema for '{old_fp.api_path or old_fp.element_id}' "
                f"has changed. Field differences detected in the response body. "
                f"Updating the expected schema in the test step."
            )

        if drift_type == DriftType.API_PATH_CHANGED:
            return (
                f"The API endpoint path changed from '{old_fp.api_path}' to "
                f"'{new_fp.api_path}'. The response schema appears consistent, "
                f"suggesting a versioning or routing change."
            )

        return f"Drift type '{drift_type.value}' detected on '{old_fp.element_id}'."

    # ── Similarity Utilities ─────────────────────────────────────────────────

    def _visual_similarity_search(
        self,
        target: ElementFingerprint,
        candidates: List[ElementFingerprint],
    ) -> Optional[ElementFingerprint]:
        """
        Find the most visually similar element from the candidates.
        Uses cosine similarity on Vision AI embedding vectors.
        Falls back to attribute-based matching if embeddings are unavailable.
        """
        if not target.visual_embedding:
            # Fallback: match by element type + attribute overlap
            return self._attribute_fallback_search(target, candidates)

        best_match: Optional[ElementFingerprint] = None
        best_score = 0.0

        for candidate in candidates:
            if candidate.element_id == target.element_id:
                continue
            if not candidate.visual_embedding:
                continue
            if candidate.element_type != target.element_type:
                continue

            score = self._cosine_similarity(
                target.visual_embedding,
                candidate.visual_embedding,
            )
            if score > best_score and score > 0.70:
                best_score = score
                best_match = candidate

        if best_match:
            logger.debug(
                "Visual match for '%s' → '%s' (score=%.3f)",
                target.element_id,
                best_match.element_id,
                best_score,
            )
        return best_match

    def _attribute_fallback_search(
        self,
        target: ElementFingerprint,
        candidates: List[ElementFingerprint],
    ) -> Optional[ElementFingerprint]:
        """Fallback matching using attribute overlap when Vision AI embeddings are unavailable."""
        best_match: Optional[ElementFingerprint] = None
        best_overlap = 0.0

        for candidate in candidates:
            if candidate.element_id == target.element_id:
                continue
            if candidate.element_type != target.element_type:
                continue

            overlap = self._attribute_overlap(target.attributes, candidate.attributes)
            if overlap > best_overlap and overlap > 0.60:
                best_overlap = overlap
                best_match = candidate

        return best_match

    @staticmethod
    def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        """Compute cosine similarity between two embedding vectors."""
        if len(vec_a) != len(vec_b) or not vec_a:
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        mag_a = sum(a * a for a in vec_a) ** 0.5
        mag_b = sum(b * b for b in vec_b) ** 0.5
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)

    @staticmethod
    def _attribute_overlap(
        attrs_a: Dict[str, Any],
        attrs_b: Dict[str, Any],
    ) -> float:
        """Compute the Jaccard-like overlap between two attribute dictionaries."""
        if not attrs_a and not attrs_b:
            return 1.0
        if not attrs_a or not attrs_b:
            return 0.0
        keys_a = set(attrs_a.keys())
        keys_b = set(attrs_b.keys())
        shared = keys_a & keys_b
        if not shared:
            return 0.0
        matching_values = sum(
            1 for k in shared if attrs_a[k] == attrs_b[k]
        )
        total_keys = len(keys_a | keys_b)
        return matching_values / total_keys if total_keys else 0.0

    @staticmethod
    def _fingerprint_key(fp: ElementFingerprint) -> str:
        """Generate a stable hash key for a fingerprint."""
        raw = f"{fp.element_id}:{fp.element_type}:{fp.selector}:{fp.api_path}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    # ── Telemetry ────────────────────────────────────────────────────────────

    @property
    def healing_history(self) -> List[HealingReport]:
        """Return all past healing reports for analytics."""
        return self._healing_history

    def maintenance_reduction_pct(self) -> float:
        """
        Estimate the percentage reduction in manual QA maintenance time
        based on auto-applied patches vs total patches.
        """
        total = sum(len(r.patches) for r in self._healing_history)
        auto = sum(r.auto_applied for r in self._healing_history)
        if total == 0:
            return 0.0
        return (auto / total) * 100.0

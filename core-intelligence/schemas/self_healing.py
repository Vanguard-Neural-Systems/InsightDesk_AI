# ──────────────────────────────────────────────────────────────────────────────
# InsightDesk AI — Self-Healing / Vision AI Schemas
# Contracts for autonomous test-journey maintenance.  The diagnostic agent
# fingerprints UI/API elements, detects drift, and emits healing patches
# that update test steps without human intervention.
# Target: 85 % reduction in manual QA maintenance time.
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── Element Fingerprinting ───────────────────────────────────────────────────

class ElementType(str, Enum):
    UI_BUTTON = "ui_button"
    UI_INPUT = "ui_input"
    UI_LINK = "ui_link"
    UI_TEXT = "ui_text"
    UI_IMAGE = "ui_image"
    API_ENDPOINT = "api_endpoint"
    API_FIELD = "api_field"


class ElementFingerprint(BaseModel):
    """
    A stable identity for a UI or API element.  The self-healing agent
    compares fingerprints across builds to detect selector / schema drift.
    """
    element_id: str = Field(..., description="Canonical identifier")
    element_type: ElementType
    selector: Optional[str] = Field(
        None, description="CSS / XPath selector (UI elements)",
    )
    api_path: Optional[str] = Field(
        None, description="HTTP path (API elements)",
    )
    attributes: Dict[str, Any] = Field(
        default_factory=dict,
        description="Snapshot of relevant attributes (text, aria-label, schema, …)",
    )
    visual_embedding: Optional[List[float]] = Field(
        None,
        description="Vision AI embedding vector for visual similarity matching",
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


# ── Test Journey ─────────────────────────────────────────────────────────────

class StepAction(str, Enum):
    CLICK = "click"
    TYPE = "type"
    NAVIGATE = "navigate"
    ASSERT_VISIBLE = "assert_visible"
    ASSERT_TEXT = "assert_text"
    API_CALL = "api_call"
    WAIT = "wait"


class JourneyStep(BaseModel):
    """A single step inside an automated test journey."""
    step_index: int
    action: StepAction
    target: ElementFingerprint
    input_value: Optional[str] = None
    expected_outcome: Optional[str] = None


class TestJourney(BaseModel):
    """A complete end-to-end test journey that the self-healing agent maintains."""
    journey_id: str
    name: str
    description: str = ""
    steps: List[JourneyStep] = Field(default_factory=list)
    last_passed: Optional[str] = Field(
        None, description="ISO-8601 timestamp of last successful run",
    )
    is_healthy: bool = True


# ── Healing Output ───────────────────────────────────────────────────────────

class DriftType(str, Enum):
    SELECTOR_CHANGED = "selector_changed"
    ATTRIBUTE_CHANGED = "attribute_changed"
    ELEMENT_REMOVED = "element_removed"
    ELEMENT_RELOCATED = "element_relocated"
    API_SCHEMA_CHANGED = "api_schema_changed"
    API_PATH_CHANGED = "api_path_changed"


class HealingPatch(BaseModel):
    """A single proposed repair for a broken test step."""
    step_index: int
    drift_type: DriftType
    old_fingerprint: ElementFingerprint
    new_fingerprint: ElementFingerprint
    confidence: float = Field(
        ..., ge=0.0, le=1.0,
        description="Model confidence that this patch is correct",
    )
    reasoning: str = Field(
        ..., description="Chain-of-thought explanation for why this patch was chosen",
    )


class HealingReport(BaseModel):
    """Aggregate report after the self-healing agent processes a broken journey."""
    journey_id: str
    patches: List[HealingPatch] = Field(default_factory=list)
    auto_applied: int = Field(
        default=0,
        description="Number of patches applied without human review",
    )
    needs_review: int = Field(
        default=0,
        description="Number of patches flagged for human review (low confidence)",
    )
    journey_healed: bool = False

# ──────────────────────────────────────────────────────────────────────────────
# InsightDesk AI — Agentic Reasoning Schemas
# Data contracts for the RAGless reasoning engine: Chain-of-Thought steps,
# tiered memory, tool invocations, and execution state tracking.
# Target: 80 % autonomous resolution · 98 % groundedness · near-zero hallucination
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── Enumerations ─────────────────────────────────────────────────────────────

class ActionType(str, Enum):
    TOOL_CALL = "tool_call"
    MEMORY_UPDATE = "memory_update"
    RESPONSE = "response"
    SELF_CORRECT = "self_correct"


class MemoryTier(str, Enum):
    """Tiered memory hierarchy for cognitive-dense reasoning."""
    WORKING = "working"       # Immediate in-prompt context
    EPISODIC = "episodic"     # Structured interaction history (JSONL / logs)
    PERSISTENT = "persistent" # Long-term knowledge graph / vector store


# ── Chain-of-Thought ─────────────────────────────────────────────────────────

class ThoughtStep(BaseModel):
    """One atomic reasoning step inside the agent's decision loop."""
    step_index: int = Field(..., description="0-based position in the chain")
    thinking: str = Field(..., description="Internal reasoning / logic chain")
    action_type: ActionType = Field(
        ...,
        description="What the agent decided to do after this thought",
    )
    action_input: Optional[Dict[str, Any]] = Field(
        None,
        description="Payload passed to the selected action (tool args, memory delta, …)",
    )
    observation: Optional[str] = Field(
        None,
        description="Result observed after executing the action",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Agent's self-assessed confidence in this step",
    )
    latency_ms: Optional[float] = None


# ── Tool Invocation ──────────────────────────────────────────────────────────

class ToolInvocation(BaseModel):
    """Record of a single MCP tool call made during reasoning."""
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Any] = None
    success: bool = True
    error: Optional[str] = None
    latency_ms: float = 0.0


# ── Execution State ──────────────────────────────────────────────────────────

class AgentExecutionState(BaseModel):
    """
    Full snapshot of an agent's reasoning session.
    This is the primary telemetry object emitted after every resolution attempt.
    """
    session_id: str = Field(..., description="Unique ID for this reasoning session")
    query: str = Field(..., description="Original user query / task description")
    steps: List[ThoughtStep] = Field(default_factory=list)
    tool_calls: List[ToolInvocation] = Field(default_factory=list)
    memory_tier_used: MemoryTier = MemoryTier.WORKING
    final_resolution: Optional[str] = Field(
        None,
        description="The agent's final answer or action summary",
    )
    autonomous_resolution: bool = Field(
        default=False,
        description="True if resolved without human escalation",
    )
    accuracy_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Groundedness score — target ≥ 0.98",
    )
    hallucination_flag: bool = Field(
        default=False,
        description="True if any step was flagged for hallucination",
    )
    total_latency_ms: float = 0.0


# ── Action Output ────────────────────────────────────────────────────────────

class ActionOutput(BaseModel):
    """Generic envelope for any backend action result."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    latency_ms: float = 0.0

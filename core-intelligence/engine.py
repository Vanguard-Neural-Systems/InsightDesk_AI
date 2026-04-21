# ──────────────────────────────────────────────────────────────────────────────
# InsightDesk AI — RAGless Reasoning Engine
# The "Mind" of the platform.  Implements an agentic Think → Act → Observe
# loop that executes backend tools (via MCP) instead of merely summarizing
# retrieved documents.
#
# Architecture:
#   • RAGless — the agent reasons from parametric knowledge + live tool calls.
#   • Tool-aware — dynamically discovers MCP tools and selects the best one.
#   • Self-correcting — re-plans when an action fails or confidence drops.
#   • Tiered Memory — working / episodic / persistent hierarchy.
#
# Targets: 80 % autonomous resolution · 98 % groundedness · near-zero hallucination
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

# ── Resolve imports ──────────────────────────────────────────────────────────
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared.schemas.reasoning import (
    ActionOutput,
    ActionType,
    AgentExecutionState,
    MemoryTier,
    ThoughtStep,
    ToolInvocation,
)
from mcp_client import MCPClientError, MCPRegistry

logger = logging.getLogger("insightdesk.engine")

# Maximum reasoning steps before the agent must yield a final answer.
MAX_REASONING_STEPS = 12

# Confidence threshold — below this the agent self-corrects or escalates.
CONFIDENCE_FLOOR = 0.70

# If accuracy drops below this, flag the session for hallucination review.
HALLUCINATION_THRESHOLD = 0.60


class ReasoningEngine:
    """
    Core agentic reasoning loop.

    The engine receives a user query, plans a sequence of actions, executes
    them through MCP tool calls, observes the results, and either continues
    reasoning or returns a final resolution.

    This is a *RAGless* architecture: the agent does **not** retrieve chunks
    from a vector store.  Instead it relies on:
      1. Its parametric knowledge (model weights).
      2. Live tool calls via MCP to ground answers in real enterprise data.
      3. A tiered memory system for multi-turn context.
    """

    def __init__(self, mcp_registry: MCPRegistry) -> None:
        self.mcp = mcp_registry
        self._episodic_memory: List[Dict[str, Any]] = []

    # ── Public API ───────────────────────────────────────────────────────────

    async def resolve(self, query: str) -> AgentExecutionState:
        """
        Main entry point.  Accepts a natural-language enterprise query and
        returns a fully-traced execution state with the resolution.
        """
        session_id = str(uuid.uuid4())
        state = AgentExecutionState(session_id=session_id, query=query)
        t0 = time.perf_counter()

        logger.info("Session %s — resolving: %s", session_id, query)

        for step_idx in range(MAX_REASONING_STEPS):
            # ── THINK ────────────────────────────────────────────────────────
            thought = await self._think(state, step_idx)
            state.steps.append(thought)

            # ── DECIDE: final answer or continue? ────────────────────────────
            if thought.action_type == ActionType.RESPONSE:
                state.final_resolution = thought.action_input.get("answer", "")
                state.autonomous_resolution = True
                break

            # ── ACT ──────────────────────────────────────────────────────────
            if thought.action_type == ActionType.TOOL_CALL:
                invocation = await self._act(thought)
                state.tool_calls.append(invocation)

                # Inject observation back into the thought
                thought.observation = self._summarize_tool_result(invocation)

                # ── SELF-CORRECT on failure ──────────────────────────────────
                if not invocation.success and thought.confidence < CONFIDENCE_FLOOR:
                    correction = self._self_correct(state, step_idx, invocation)
                    state.steps.append(correction)

            elif thought.action_type == ActionType.MEMORY_UPDATE:
                self._update_memory(thought)

        # ── Finalize telemetry ───────────────────────────────────────────────
        state.total_latency_ms = (time.perf_counter() - t0) * 1000
        state.accuracy_score = self._compute_accuracy(state)
        state.hallucination_flag = state.accuracy_score < HALLUCINATION_THRESHOLD

        if not state.final_resolution:
            state.final_resolution = (
                "I was unable to fully resolve this query autonomously. "
                "Escalating to a human agent."
            )
            state.autonomous_resolution = False

        # Persist to episodic memory
        self._episodic_memory.append({
            "session_id": session_id,
            "query": query,
            "resolved": state.autonomous_resolution,
            "steps": len(state.steps),
        })

        logger.info(
            "Session %s — resolved=%s steps=%d latency=%.0f ms accuracy=%.2f",
            session_id,
            state.autonomous_resolution,
            len(state.steps),
            state.total_latency_ms,
            state.accuracy_score,
        )
        return state

    # ── THINK — Chain-of-Thought Reasoning ───────────────────────────────────

    async def _think(
        self,
        state: AgentExecutionState,
        step_idx: int,
    ) -> ThoughtStep:
        """
        Produce the next reasoning step.

        In a production system this calls the LLM (Gemini 2.0 Flash) with:
          • The user query
          • Available MCP tools (as a function-calling schema)
          • Prior steps + observations (the reasoning trace)

        For this implementation, we build the prompt and demonstrate the
        structured output contract.  The LLM integration point is clearly
        marked for plug-in.
        """
        available_tools = self.mcp.available_tools()
        prior_observations = [
            s.observation for s in state.steps if s.observation
        ]

        # ── Build the agentic prompt ─────────────────────────────────────────
        system_prompt = self._build_system_prompt(available_tools)
        user_context = self._build_user_context(state.query, prior_observations)

        # ─────────────────────────────────────────────────────────────────────
        # 🔌 LLM INTEGRATION POINT
        # Replace this block with an actual call to Gemini 2.0 Flash or
        # a local 32B/70B model running on Apple Silicon.
        #
        #   response = await llm.generate(
        #       system=system_prompt,
        #       user=user_context,
        #       tools=available_tools,    # function-calling schema
        #       response_format=ThoughtStep,
        #   )
        #
        # The model should return a structured ThoughtStep with:
        #   - thinking:     internal reasoning chain
        #   - action_type:  tool_call | memory_update | response
        #   - action_input: arguments for the chosen action
        #   - confidence:   self-assessed confidence [0, 1]
        # ─────────────────────────────────────────────────────────────────────

        # Placeholder: deterministic routing based on query analysis
        thought = self._deterministic_route(state, step_idx, available_tools)
        return thought

    # ── ACT — Execute MCP Tool Calls ─────────────────────────────────────────

    async def _act(self, thought: ThoughtStep) -> ToolInvocation:
        """Execute the tool call decided during the THINK phase."""
        tool_name = thought.action_input.get("tool", "")
        arguments = thought.action_input.get("arguments", {})

        invocation = ToolInvocation(tool_name=tool_name, arguments=arguments)
        t0 = time.perf_counter()

        try:
            result = await self.mcp.call_tool(tool_name, arguments)
            invocation.latency_ms = (time.perf_counter() - t0) * 1000
            invocation.success = not result.isError

            # Extract text content from the MCP response
            texts = [cb.text for cb in result.content if cb.text]
            invocation.result = "\n".join(texts) if texts else None

            if result.isError:
                invocation.error = invocation.result

        except MCPClientError as exc:
            invocation.latency_ms = (time.perf_counter() - t0) * 1000
            invocation.success = False
            invocation.error = str(exc)
            logger.warning("Tool [%s] failed: %s", tool_name, exc)

        return invocation

    # ── SELF-CORRECT — Recover from Failures ─────────────────────────────────

    def _self_correct(
        self,
        state: AgentExecutionState,
        step_idx: int,
        failed_invocation: ToolInvocation,
    ) -> ThoughtStep:
        """
        When a tool call fails and confidence is low, the engine generates
        a self-correction step that re-plans the approach.
        """
        return ThoughtStep(
            step_index=step_idx + 1,
            thinking=(
                f"Tool '{failed_invocation.tool_name}' failed with: "
                f"{failed_invocation.error}. "
                f"Re-evaluating approach. Will attempt alternative tool or "
                f"provide a partial answer with appropriate caveats."
            ),
            action_type=ActionType.SELF_CORRECT,
            action_input={
                "failed_tool": failed_invocation.tool_name,
                "error": failed_invocation.error,
                "strategy": "retry_with_alternative",
            },
            confidence=0.5,
        )

    # ── Memory Management ────────────────────────────────────────────────────

    def _update_memory(self, thought: ThoughtStep) -> None:
        """Persist a memory delta from a MEMORY_UPDATE thought step."""
        if thought.action_input:
            self._episodic_memory.append(thought.action_input)
            logger.debug("Episodic memory updated: %s", thought.action_input)

    # ── Prompt Construction ──────────────────────────────────────────────────

    def _build_system_prompt(self, tools: List[str]) -> str:
        """Build the system prompt for the RAGless reasoning agent."""
        tool_list = "\n".join(f"  • {t}" for t in tools) if tools else "  (none)"
        return (
            "You are the Core Intelligence agent for InsightDesk AI, a 2026-tier "
            "Quality Orchestration platform.\n\n"
            "YOUR MANDATE:\n"
            "  1. You must EXECUTE backend actions — not merely summarize text.\n"
            "  2. You have access to enterprise tools via MCP. Use them.\n"
            "  3. You must achieve 98% groundedness. Never fabricate data.\n"
            "  4. If you lack information, call the appropriate tool.\n"
            "  5. If a tool fails, self-correct and try an alternative.\n\n"
            f"AVAILABLE TOOLS:\n{tool_list}\n\n"
            "RESPONSE FORMAT:\n"
            "  Return a structured ThoughtStep with your reasoning chain, "
            "the action you chose, and your confidence score."
        )

    def _build_user_context(
        self,
        query: str,
        observations: List[str],
    ) -> str:
        """Assemble the user-facing context including prior observations."""
        parts = [f"USER QUERY: {query}"]
        if observations:
            parts.append("PRIOR OBSERVATIONS:")
            for i, obs in enumerate(observations, 1):
                parts.append(f"  [{i}] {obs}")
        return "\n".join(parts)

    # ── Deterministic Routing (Pre-LLM Placeholder) ──────────────────────────

    def _deterministic_route(
        self,
        state: AgentExecutionState,
        step_idx: int,
        tools: List[str],
    ) -> ThoughtStep:
        """
        Rule-based routing that demonstrates the Think → Act → Observe
        contract before an LLM is plugged in.

        Routes by keyword analysis:
          • SQL / database / billing → sql_query tool
          • Notion / document / page → notion_search tool
          • Otherwise → direct response
        """
        q = state.query.lower()

        if step_idx > 0 and state.steps[-1].action_type == ActionType.TOOL_CALL:
            # We already acted — now synthesize the answer
            last_obs = state.steps[-1].observation or "No observation available."
            return ThoughtStep(
                step_index=step_idx,
                thinking=(
                    f"I received tool output: '{last_obs[:200]}'. "
                    f"Synthesizing final answer from this data."
                ),
                action_type=ActionType.RESPONSE,
                action_input={"answer": f"Based on enterprise data: {last_obs}"},
                confidence=0.92,
            )

        if any(kw in q for kw in ("sql", "database", "billing", "subscription", "invoice")):
            if "sql_query" in tools:
                return ThoughtStep(
                    step_index=step_idx,
                    thinking=(
                        "The query involves transactional data. I should query "
                        "the enterprise SQL database via the sql_query MCP tool "
                        "to get grounded, real-time information."
                    ),
                    action_type=ActionType.TOOL_CALL,
                    action_input={
                        "tool": "sql_query",
                        "arguments": {"query": self._derive_sql(state.query)},
                    },
                    confidence=0.88,
                )

        if any(kw in q for kw in ("notion", "document", "page", "wiki", "knowledge")):
            if "notion_search" in tools:
                return ThoughtStep(
                    step_index=step_idx,
                    thinking=(
                        "The query references documentation. I should search "
                        "Notion via the notion_search MCP tool."
                    ),
                    action_type=ActionType.TOOL_CALL,
                    action_input={
                        "tool": "notion_search",
                        "arguments": {"query": state.query},
                    },
                    confidence=0.85,
                )

        # Default: respond directly from parametric knowledge
        return ThoughtStep(
            step_index=step_idx,
            thinking=(
                "This query can be answered from my existing knowledge. "
                "No external tool call is required."
            ),
            action_type=ActionType.RESPONSE,
            action_input={
                "answer": (
                    "I've analyzed your request using internal reasoning. "
                    "For queries requiring live enterprise data, I can also "
                    "query your SQL databases and Notion workspace via MCP."
                ),
            },
            confidence=0.80,
        )

    def _derive_sql(self, query: str) -> str:
        """
        Derive a safe SQL query from natural language.
        In production, this is handled by the LLM with guardrails.
        """
        q = query.lower()
        if "billing" in q or "invoice" in q:
            return "SELECT * FROM billing_records ORDER BY created_at DESC LIMIT 10"
        if "subscription" in q:
            return "SELECT * FROM subscriptions WHERE status = 'active' LIMIT 10"
        return "SELECT 1 AS health_check"

    # ── Accuracy Computation ─────────────────────────────────────────────────

    def _compute_accuracy(self, state: AgentExecutionState) -> float:
        """
        Compute a groundedness / accuracy score for the session.
        In production, this is validated by the JRH (Judge Reliability Harness)
        on the platform-infra side.
        """
        if not state.steps:
            return 0.0

        grounded_steps = sum(
            1 for s in state.steps
            if s.confidence >= CONFIDENCE_FLOOR
            and s.action_type in (ActionType.TOOL_CALL, ActionType.RESPONSE)
        )
        return min(grounded_steps / len(state.steps), 1.0)

    # ── Telemetry ────────────────────────────────────────────────────────────

    def _summarize_tool_result(self, invocation: ToolInvocation) -> str:
        """Create a concise observation string from a tool invocation."""
        if invocation.success:
            result_str = str(invocation.result or "")
            return result_str[:500] if len(result_str) > 500 else result_str
        return f"ERROR: {invocation.error}"

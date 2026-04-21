# ──────────────────────────────────────────────────────────────────────────────
# InsightDesk AI — Judge Model Abstractions
# Abstract base class and concrete implementations for the three independent
# judge providers used by the JRH ensemble.
#
# Design:  "Judge-Generator Separation" — the judge models are ALWAYS from
#          different providers than the model that generated the original
#          response, ensuring objective, unbiased scoring.
#
# Providers:
#   • NVIDIA NIM (Llama 3.1 70B)
#   • Groq       (Llama 3 70B)
#   • Google     (Gemini 2.0 Flash)
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import abc
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from src.config import settings

logger = logging.getLogger("insightdesk.infra.judges")


# ── Judge Score Data Class ──────────────────────────────────────────────────

@dataclass
class JudgeScore:
    """Result from a single judge evaluation."""

    provider: str
    model: str
    score: float               # 0-10
    reasoning: str             # Chain-of-thought from the judge
    confidence: float = 1.0    # 0-1
    latency_ms: float = 0.0

    # G-Eval sub-scores (optional, filled when G-Eval rubric is used)
    coherence: Optional[float] = None
    consistency: Optional[float] = None
    fluency: Optional[float] = None
    relevance: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "score": self.score,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "latency_ms": self.latency_ms,
            "coherence": self.coherence,
            "consistency": self.consistency,
            "fluency": self.fluency,
            "relevance": self.relevance,
        }


# ── Evaluation Prompt Builder ───────────────────────────────────────────────

_JUDGE_SYSTEM_PROMPT = """\
You are an expert AI quality judge for the InsightDesk AI platform.
Your task is to evaluate the quality of an AI agent's response to a user query.

EVALUATION CRITERIA (score each 0-10):
1. COHERENCE  — Is the reasoning chain logical and well-structured?
2. CONSISTENCY — Does the response align with the tool results and observations?
3. FLUENCY    — Is the final resolution clearly and professionally communicated?
4. RELEVANCE  — Does the response directly address the user's query?

INSTRUCTIONS:
- First, provide a chain-of-thought analysis of the response quality.
- Then, provide scores for each criterion (0-10).
- Finally, provide an overall score (0-10) and your confidence (0.0-1.0).

Respond in STRICT JSON format:
{
  "reasoning": "<your chain-of-thought analysis>",
  "coherence": <0-10>,
  "consistency": <0-10>,
  "fluency": <0-10>,
  "relevance": <0-10>,
  "overall_score": <0-10>,
  "confidence": <0.0-1.0>
}
"""


def _build_evaluation_prompt(
    query: str,
    thought_chain: List[Dict[str, Any]],
    final_resolution: str,
    tool_calls: List[Dict[str, Any]],
) -> str:
    """Build the user-facing evaluation prompt for a judge."""
    steps_text = ""
    for step in thought_chain:
        steps_text += (
            f"  Step {step.get('step_index', '?')}: "
            f"[{step.get('action_type', 'unknown')}] "
            f"{step.get('thinking', 'N/A')}\n"
            f"    → Observation: {step.get('observation', 'N/A')}\n"
            f"    → Confidence: {step.get('confidence', 0.0)}\n"
        )

    tools_text = ""
    for tc in tool_calls:
        tools_text += (
            f"  Tool: {tc.get('tool_name', '?')} "
            f"→ Success: {tc.get('success', '?')} "
            f"→ Latency: {tc.get('latency_ms', 0)}ms\n"
        )

    return (
        f"USER QUERY:\n{query}\n\n"
        f"AGENT REASONING CHAIN:\n{steps_text}\n"
        f"TOOL CALLS:\n{tools_text or '  (none)'}\n\n"
        f"FINAL RESOLUTION:\n{final_resolution}\n\n"
        f"Please evaluate the quality of this interaction."
    )


# ── Abstract Base Judge ─────────────────────────────────────────────────────

class BaseJudge(abc.ABC):
    """
    Abstract base class for all judge model implementations.

    Subclasses must implement ``_call_model()`` which handles the
    provider-specific HTTP call and returns the raw response text.
    """

    provider: str
    model: str

    @abc.abstractmethod
    async def _call_model(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Send the evaluation prompt to the model and return the raw text response."""
        ...

    async def evaluate(
        self,
        query: str,
        thought_chain: List[Dict[str, Any]],
        final_resolution: str,
        tool_calls: List[Dict[str, Any]],
    ) -> JudgeScore:
        """
        Run a full evaluation cycle:
          1. Build the prompt
          2. Call the model
          3. Parse the JSON response into a JudgeScore
        """
        user_prompt = _build_evaluation_prompt(
            query, thought_chain, final_resolution or "(no resolution)", tool_calls,
        )

        start = time.perf_counter()
        try:
            raw_response = await self._call_model(_JUDGE_SYSTEM_PROMPT, user_prompt)
            latency = (time.perf_counter() - start) * 1000

            # Parse JSON from the response
            parsed = self._parse_response(raw_response)

            return JudgeScore(
                provider=self.provider,
                model=self.model,
                score=parsed.get("overall_score", 5.0),
                reasoning=parsed.get("reasoning", raw_response),
                confidence=parsed.get("confidence", 0.5),
                latency_ms=latency,
                coherence=parsed.get("coherence"),
                consistency=parsed.get("consistency"),
                fluency=parsed.get("fluency"),
                relevance=parsed.get("relevance"),
            )
        except Exception as exc:
            latency = (time.perf_counter() - start) * 1000
            logger.error(
                "Judge %s/%s failed: %s", self.provider, self.model, exc,
            )
            # Return a neutral score on failure so the ensemble can still function
            return JudgeScore(
                provider=self.provider,
                model=self.model,
                score=5.0,
                reasoning=f"Judge evaluation failed: {exc}",
                confidence=0.0,
                latency_ms=latency,
            )

    @staticmethod
    def _parse_response(raw: str) -> Dict[str, Any]:
        """Extract JSON from a model response, handling markdown code fences."""
        text = raw.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON within the text
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
            return {"reasoning": raw, "overall_score": 5.0, "confidence": 0.1}


# ── NVIDIA Judge ────────────────────────────────────────────────────────────

class NvidiaJudge(BaseJudge):
    """Judge powered by NVIDIA NIM (Llama 3.1 70B). Uses OpenAI-compatible SDK endpoint."""

    provider = "nvidia"

    def __init__(self) -> None:
        self.model = settings.JUDGE_NVIDIA_MODEL
        self._api_key = settings.JUDGE_NVIDIA_API_KEY
        self._base_url = settings.JUDGE_NVIDIA_BASE_URL

    async def _call_model(self, system_prompt: str, user_prompt: str) -> str:
        if not self._api_key:
            return json.dumps({
                "reasoning": "NVIDIA API key not configured — returning mock score.",
                "coherence": 7, "consistency": 7, "fluency": 8, "relevance": 7,
                "overall_score": 7.25, "confidence": 0.3,
            })

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]


# ── Groq Judge ─────────────────────────────────────────────────────────

class GroqJudge(BaseJudge):
    """Judge powered by Groq (Llama 3 70B). Uses OpenAI-compatible SDK endpoint."""

    provider = "groq"

    def __init__(self) -> None:
        self.model = settings.JUDGE_GROQ_MODEL
        self._api_key = settings.JUDGE_GROQ_API_KEY
        self._base_url = settings.JUDGE_GROQ_BASE_URL

    async def _call_model(self, system_prompt: str, user_prompt: str) -> str:
        if not self._api_key:
            return json.dumps({
                "reasoning": "Groq API key not configured — returning mock score.",
                "coherence": 8, "consistency": 7, "fluency": 7, "relevance": 8,
                "overall_score": 7.5, "confidence": 0.3,
            })

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]


# ── Gemini Judge ────────────────────────────────────────────────────────────

class GeminiJudge(BaseJudge):
    """Judge powered by Google (Gemini 2.0 Flash)."""

    provider = "gemini"

    def __init__(self) -> None:
        self.model = settings.JUDGE_GEMINI_MODEL
        self._api_key = settings.JUDGE_GEMINI_API_KEY
        self._base_url = settings.JUDGE_GEMINI_BASE_URL

    async def _call_model(self, system_prompt: str, user_prompt: str) -> str:
        if not self._api_key:
            return json.dumps({
                "reasoning": "Gemini API key not configured — returning mock score.",
                "coherence": 7, "consistency": 8, "fluency": 7, "relevance": 7,
                "overall_score": 7.25, "confidence": 0.3,
            })

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self._base_url}/models/{self.model}:generateContent",
                params={"key": self._api_key},
                json={
                    "system_instruction": {"parts": [{"text": system_prompt}]},
                    "contents": [
                        {"parts": [{"text": user_prompt}]},
                    ],
                    "generationConfig": {
                        "temperature": 0.1,
                        "responseMimeType": "application/json",
                    },
                },
            )
            resp.raise_for_status()
            candidates = resp.json().get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "{}")
            return "{}"


# ── Factory ─────────────────────────────────────────────────────────────────

def create_default_judges() -> List[BaseJudge]:
    """Instantiate the default 3-judge panel (one per provider)."""
    return [NvidiaJudge(), GroqJudge(), GeminiJudge()]

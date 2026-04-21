# ──────────────────────────────────────────────────────────────────────────────
# InsightDesk AI — Multi-Provider LLM Router
# Abstracts the reasoning engine's connection to different LLM backends.
# Supports Google GenAI (Gemini 2.0 Flash) and Groq (Llama 3).
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types as genai_types
from groq import Groq

from shared.schemas.reasoning import ActionType, ThoughtStep

logger = logging.getLogger("insightdesk.engine.llm")


class MultiProviderRouter:
    """Routes inference requests to the configured LLM provider."""

    def __init__(self):
        self.provider = os.getenv("PRIMARY_LLM_PROVIDER", "gemini").lower()
        self.gemini_client = None
        self.groq_client = None

        if self.provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key or api_key == "your-gemini-api-key-here":
                logger.warning("GEMINI_API_KEY not set. Engine will operate in mock mode.")
            else:
                self.gemini_client = genai.Client(api_key=api_key)
        elif self.provider == "groq":
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key or api_key == "your-groq-api-key-here":
                logger.warning("GROQ_API_KEY not set. Engine will operate in mock mode.")
            else:
                self.groq_client = Groq(api_key=api_key)
        else:
            logger.warning(f"Unknown provider '{self.provider}'. Falling back to mock mode.")

    async def generate_thought(
        self,
        system_prompt: str,
        user_context: str,
        tools: List[str],
        step_idx: int,
        state_query: str,
        mock_fallback: Any = None,
    ) -> ThoughtStep:
        """
        Calls the active LLM provider to generate the next ThoughtStep.
        If no API key is configured, falls back to the deterministic router.
        """
        if self.provider == "gemini" and self.gemini_client:
            return await self._call_gemini(system_prompt, user_context, tools, step_idx)
        elif self.provider == "groq" and self.groq_client:
            return await self._call_groq(system_prompt, user_context, tools, step_idx)
        
        # Fallback to deterministic routing (Mock mode)
        logger.debug("Using mock deterministic router for step %d", step_idx)
        return mock_fallback(step_idx, tools)

    async def _call_gemini(self, system_prompt: str, user_context: str, tools: List[str], step_idx: int) -> ThoughtStep:
        """Execute inference using Gemini 2.0 Flash with Structured Outputs."""
        model_name = "gemini-2.5-flash"
        
        # Define the expected JSON schema for ThoughtStep
        thought_schema = {
            "type": "OBJECT",
            "properties": {
                "thinking": {"type": "STRING"},
                "action_type": {"type": "STRING", "enum": ["tool_call", "memory_update", "response", "self_correct"]},
                "action_input": {"type": "OBJECT"},
                "confidence": {"type": "NUMBER"}
            },
            "required": ["thinking", "action_type", "action_input", "confidence"]
        }

        try:
            # We use synchronous call here for simplicity, but in production we'd use async
            # Since google-genai supports async via client.aio, let's use it if available, 
            # otherwise wrap in run_in_executor
            import asyncio
            loop = asyncio.get_event_loop()
            
            def _sync_call():
                return self.gemini_client.models.generate_content(
                    model=model_name,
                    contents=user_context,
                    config=genai_types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        response_mime_type="application/json",
                        response_schema=thought_schema,
                        temperature=0.2,
                    )
                )
            
            response = await loop.run_in_executor(None, _sync_call)
            
            data = json.loads(response.text)
            return ThoughtStep(
                step_index=step_idx,
                thinking=data.get("thinking", "No reasoning provided"),
                action_type=ActionType(data.get("action_type", "response")),
                action_input=data.get("action_input", {}),
                confidence=float(data.get("confidence", 0.8))
            )
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return ThoughtStep(
                step_index=step_idx,
                thinking=f"Error calling LLM: {e}",
                action_type=ActionType.RESPONSE,
                action_input={"answer": "I encountered an internal error while processing your request."},
                confidence=0.0
            )

    async def _call_groq(self, system_prompt: str, user_context: str, tools: List[str], step_idx: int) -> ThoughtStep:
        """Execute inference using Groq (Llama 3 70B) with JSON mode."""
        model_name = "llama3-70b-8192"
        
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            
            def _sync_call():
                return self.groq_client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt + "\n\nRespond ONLY with a valid JSON object matching the ThoughtStep schema."},
                        {"role": "user", "content": user_context}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.2,
                )
            
            response = await loop.run_in_executor(None, _sync_call)
            
            data = json.loads(response.choices[0].message.content)
            return ThoughtStep(
                step_index=step_idx,
                thinking=data.get("thinking", "No reasoning provided"),
                action_type=ActionType(data.get("action_type", "response")),
                action_input=data.get("action_input", {}),
                confidence=float(data.get("confidence", 0.8))
            )
            
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return ThoughtStep(
                step_index=step_idx,
                thinking=f"Error calling LLM: {e}",
                action_type=ActionType.RESPONSE,
                action_input={"answer": "I encountered an internal error while processing your request."},
                confidence=0.0
            )

# ──────────────────────────────────────────────────────────────────────────────
# InsightDesk AI — Core Intelligence Service
# FastAPI application that exposes the Reasoning Engine, WebRTC Voice
# Pipeline, and Self-Healing Engine as HTTP/WebSocket endpoints.
#
# This is the primary entry point for the core-intelligence microservice.
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

# ── Resolve imports ──────────────────────────────────────────────────────────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared.schemas.mcp import CallToolResult
from shared.schemas.reasoning import AgentExecutionState
from shared.schemas.voice import ICECandidate, SDPAnswer, SDPOffer, VoiceSession
from shared.schemas.self_healing import (
    ElementFingerprint,
    HealingReport,
    TestJourney,
)

from engine import ReasoningEngine
from mcp_client import MCPClient, MCPRegistry
from self_healing import SelfHealingEngine
from voice_handler import VoiceHandler

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-30s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("insightdesk.main")


# ── Startup / Shutdown ───────────────────────────────────────────────────────

mcp_registry = MCPRegistry()
reasoning_engine: Optional[ReasoningEngine] = None
voice_handler: Optional[VoiceHandler] = None
self_healing_engine = SelfHealingEngine()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — initialize MCP connections and engine modules."""
    global reasoning_engine, voice_handler

    # ── Register MCP servers (configure via env vars in production) ───────
    mcp_url = os.getenv("MCP_SERVER_URL", "http://localhost:8100")
    mcp_key = os.getenv("MCP_API_KEY")

    mcp_registry.register(
        MCPClient(
            server_url=mcp_url,
            server_name="enterprise-data",
            api_key=mcp_key,
        )
    )

    try:
        await mcp_registry.initialize_all()
        logger.info("MCP registry initialized — tools: %s", mcp_registry.available_tools())
    except Exception as exc:
        logger.warning("MCP initialization deferred (servers not yet available): %s", exc)

    # ── Initialize engines ───────────────────────────────────────────────
    reasoning_engine = ReasoningEngine(mcp_registry=mcp_registry)
    voice_handler = VoiceHandler()

    logger.info("══════════════════════════════════════════════════════════")
    logger.info("  InsightDesk AI — Core Intelligence Service ONLINE")
    logger.info("  Reasoning: RAGless · Voice: WebRTC/UDP · Healing: Auto")
    logger.info("══════════════════════════════════════════════════════════")

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────
    if voice_handler:
        await voice_handler.close_all()
    logger.info("Core Intelligence Service shutdown complete.")


# ── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="InsightDesk AI — Core Intelligence",
    description=(
        "The 'Mind and High-Speed Body' of InsightDesk AI. "
        "Exposes RAGless reasoning, WebRTC voice, and autonomous self-healing "
        "as production-grade API endpoints."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════════════════════
#  HEALTH & STATUS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/", tags=["Status"])
async def root():
    return {
        "service": "InsightDesk AI — Core Intelligence",
        "version": "2.0.0",
        "status": "operational",
        "capabilities": [
            "ragless_reasoning",
            "webrtc_voice",
            "self_healing_qa",
            "mcp_data_access",
        ],
    }


@app.get("/health", tags=["Status"])
async def health_check():
    return {
        "status": "healthy",
        "mcp_tools_available": len(mcp_registry.available_tools()),
        "active_voice_sessions": 0,
        "registered_journeys": len(self_healing_engine.list_journeys()),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  REASONING ENGINE — Action-Oriented RAGless Agent
# ══════════════════════════════════════════════════════════════════════════════

class ResolveRequest(BaseModel):
    query: str = Field(..., description="The enterprise query to resolve autonomously")


@app.post(
    "/reasoning/resolve",
    response_model=AgentExecutionState,
    tags=["Reasoning"],
    summary="Resolve a query using the RAGless reasoning engine",
)
async def resolve_query(req: ResolveRequest):
    """
    Submit an enterprise query for autonomous resolution.

    The engine will:
      1. Think — plan the best approach using Chain-of-Thought.
      2. Act — execute MCP tool calls (SQL, Notion, billing APIs).
      3. Observe — analyse tool results and self-correct if needed.
      4. Respond — return a grounded, traceable resolution.
    """
    if not reasoning_engine:
        raise HTTPException(503, "Reasoning engine not initialized")
    return await reasoning_engine.resolve(req.query)


class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


@app.post(
    "/reasoning/tool",
    response_model=CallToolResult,
    tags=["Reasoning"],
    summary="Directly invoke an MCP tool",
)
async def direct_tool_call(req: ToolCallRequest):
    """Directly invoke a registered MCP tool (bypassing the reasoning loop)."""
    try:
        return await mcp_registry.call_tool(req.tool_name, req.arguments)
    except Exception as exc:
        raise HTTPException(400, str(exc))


@app.get(
    "/reasoning/tools",
    tags=["Reasoning"],
    summary="List all available MCP tools",
)
async def list_mcp_tools():
    """Return all tools available across connected MCP servers."""
    return {"tools": mcp_registry.available_tools()}


# ══════════════════════════════════════════════════════════════════════════════
#  VOICE — WebRTC Zero-Latency Pipeline
# ══════════════════════════════════════════════════════════════════════════════

@app.post(
    "/voice/offer",
    response_model=Dict[str, Any],
    tags=["Voice"],
    summary="Initiate a WebRTC voice session",
)
async def voice_offer(offer: SDPOffer):
    """
    Accept a WebRTC SDP offer and return the server's SDP answer.
    After this handshake, audio flows over UDP — no WebSocket needed.
    Target TTFA: < 300 ms.
    """
    if not voice_handler:
        raise HTTPException(503, "Voice handler not initialized")

    session_id, answer = await voice_handler.create_session(offer)
    return {
        "session_id": session_id,
        "answer": answer.model_dump(),
    }


@app.post(
    "/voice/ice-candidate",
    tags=["Voice"],
    summary="Add a trickle ICE candidate",
)
async def add_ice_candidate(session_id: str, candidate: ICECandidate):
    """Add an ICE candidate to an active WebRTC session."""
    if not voice_handler:
        raise HTTPException(503, "Voice handler not initialized")

    try:
        await voice_handler.add_ice_candidate(session_id, candidate)
        return {"status": "added"}
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@app.get(
    "/voice/session/{session_id}",
    response_model=Optional[VoiceSession],
    tags=["Voice"],
    summary="Get voice session telemetry",
)
async def get_voice_session(session_id: str):
    """Retrieve TTFA, MOS, jitter, and status for a voice session."""
    if not voice_handler:
        raise HTTPException(503, "Voice handler not initialized")

    session = voice_handler.get_session(session_id)
    if not session:
        raise HTTPException(404, f"Session {session_id} not found")
    return session


# ══════════════════════════════════════════════════════════════════════════════
#  SELF-HEALING — Autonomous Test Journey Maintenance
# ══════════════════════════════════════════════════════════════════════════════

@app.post(
    "/healing/journeys",
    tags=["Self-Healing"],
    summary="Register a test journey for autonomous monitoring",
)
async def register_journey(journey: TestJourney):
    """Register a new test journey. The engine will monitor it for drift."""
    self_healing_engine.register_journey(journey)
    return {"status": "registered", "journey_id": journey.journey_id}


@app.get(
    "/healing/journeys",
    response_model=List[TestJourney],
    tags=["Self-Healing"],
    summary="List all registered test journeys",
)
async def list_journeys():
    """Return all registered test journeys and their health status."""
    return self_healing_engine.list_journeys()


class HealRequest(BaseModel):
    journey_id: str
    current_fingerprints: List[ElementFingerprint]


@app.post(
    "/healing/heal",
    response_model=HealingReport,
    tags=["Self-Healing"],
    summary="Trigger self-healing for a test journey",
)
async def heal_journey(req: HealRequest):
    """
    Run the full self-healing cycle:
      1. Detect drift between current and last-known-good fingerprints.
      2. Generate healing patches with confidence scores.
      3. Auto-apply high-confidence patches.
      4. Flag low-confidence patches for human review.
    """
    try:
        return await self_healing_engine.heal_journey(
            req.journey_id,
            req.current_fingerprints,
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@app.get(
    "/healing/stats",
    tags=["Self-Healing"],
    summary="Get self-healing statistics",
)
async def healing_stats():
    """Return aggregate self-healing metrics."""
    return {
        "total_healing_runs": len(self_healing_engine.healing_history),
        "maintenance_reduction_pct": round(
            self_healing_engine.maintenance_reduction_pct(), 1
        ),
        "registered_journeys": len(self_healing_engine.list_journeys()),
    }

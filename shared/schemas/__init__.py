# ──────────────────────────────────────────────────────────────────────────────
# InsightDesk AI — Shared Protocol Schemas
# Source of Truth for all cross-service data contracts.
# ──────────────────────────────────────────────────────────────────────────────

from shared.schemas.mcp import (
    MCPTool,
    MCPToolParameter,
    CallToolRequest,
    CallToolResult,
    ListToolsResult,
    ReadResourceRequest,
    ReadResourceResult,
)
from shared.schemas.voice import (
    ICEServer,
    WebRTCConfig,
    SDPOffer,
    SDPAnswer,
    ICECandidate,
    VoiceSession,
    AudioChunk,
)
from shared.schemas.reasoning import (
    ThoughtStep,
    MemoryTier,
    AgentExecutionState,
    ActionOutput,
    ToolInvocation,
)
from shared.schemas.self_healing import (
    ElementFingerprint,
    JourneyStep,
    TestJourney,
    HealingPatch,
    HealingReport,
)

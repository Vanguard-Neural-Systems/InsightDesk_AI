# ──────────────────────────────────────────────────────────────────────────────
# InsightDesk AI — WebRTC Voice Transport Schemas
# Zero-latency voice pipeline contracts.  UDP-based WebRTC eliminates
# head-of-line blocking; target TTFA < 300 ms to match human reaction speed.
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


# ── ICE / STUN / TURN ───────────────────────────────────────────────────────

class ICEServer(BaseModel):
    """STUN/TURN server used for NAT traversal."""
    urls: List[str] = Field(..., description="stun: or turn: URI list")
    username: Optional[str] = None
    credential: Optional[str] = None


class WebRTCConfig(BaseModel):
    """Client-side RTCPeerConnection configuration."""
    iceServers: List[ICEServer] = Field(default_factory=list)
    sdpSemantics: str = "unified-plan"
    bundlePolicy: str = "max-bundle"


# ── SDP Signaling ────────────────────────────────────────────────────────────

class SDPOffer(BaseModel):
    """WebRTC SDP offer from the client."""
    type: str = "offer"
    sdp: str = Field(..., description="Session Description Protocol payload")


class SDPAnswer(BaseModel):
    """WebRTC SDP answer from the server."""
    type: str = "answer"
    sdp: str = Field(..., description="Session Description Protocol payload")


class ICECandidate(BaseModel):
    """Trickle ICE candidate exchanged during negotiation."""
    candidate: str
    sdpMid: Optional[str] = None
    sdpMLineIndex: Optional[int] = None
    usernameFragment: Optional[str] = None


# ── Session & Telemetry ──────────────────────────────────────────────────────

class SessionStatus(str, Enum):
    INITIALIZING = "initializing"
    NEGOTIATING = "negotiating"
    CONNECTED = "connected"
    STREAMING = "streaming"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class VoiceSession(BaseModel):
    """Tracks a single voice interaction lifecycle."""
    session_id: str
    status: SessionStatus = SessionStatus.INITIALIZING
    ttfa_ms: Optional[float] = Field(
        None,
        description="Time to First Audio in ms — must be < 300 for 2026 target",
    )
    jitter_ms: Optional[float] = None
    packet_loss_pct: Optional[float] = None
    mos_score: Optional[float] = Field(
        None,
        description="Mean Opinion Score (1-5), target ≥ 4.3",
    )


class AudioChunk(BaseModel):
    """A single audio frame transported over the WebRTC data channel."""
    session_id: str
    sequence: int = Field(..., description="Monotonically increasing frame number")
    codec: str = Field(default="opus", description="Audio codec (opus recommended)")
    sample_rate: int = Field(default=48000)
    channels: int = Field(default=1)
    payload_b64: str = Field(..., description="Base64-encoded raw audio bytes")
    is_barge_in: bool = Field(
        default=False,
        description="True if the user interrupted the AI mid-utterance",
    )

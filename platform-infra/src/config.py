# ──────────────────────────────────────────────────────────────────────────────
# InsightDesk AI — Platform Infrastructure Configuration
# Centralized settings for database, judge models, SLA thresholds, and
# synchronization paths.  Reads from environment variables with sane defaults.
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Platform Infrastructure global configuration."""

    # ── Service ──────────────────────────────────────────────────────────────
    SERVICE_NAME: str = "InsightDesk AI — Platform Infrastructure"
    SERVICE_VERSION: str = "2.0.0"
    DEBUG: bool = False

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./insightdesk_infra.db",
        description=(
            "Async database URL.  Production: postgresql+asyncpg://user:pass@host/db  "
            "Local dev: sqlite+aiosqlite:///./insightdesk_infra.db"
        ),
    )
    DB_ECHO: bool = Field(
        default=False,
        description="Echo all SQL statements to the log (dev only).",
    )

    # ── Judge Model Endpoints (JRH) ─────────────────────────────────────────
    JUDGE_NVIDIA_API_KEY: Optional[str] = None
    JUDGE_NVIDIA_MODEL: str = "meta/llama-3.1-70b-instruct"
    JUDGE_NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"

    JUDGE_GROQ_API_KEY: Optional[str] = None
    JUDGE_GROQ_MODEL: str = "llama3-70b-8192"
    JUDGE_GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"

    JUDGE_GEMINI_API_KEY: Optional[str] = None
    JUDGE_GEMINI_MODEL: str = "gemini-2.0-flash"
    JUDGE_GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"

    # ── JRH Thresholds ──────────────────────────────────────────────────────
    JRH_ENTROPY_THRESHOLD: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description=(
            "Shannon entropy threshold across 3 judge scores.  "
            "If exceeded, the interaction is routed for human calibration."
        ),
    )
    JRH_MIN_CONSENSUS_SCORE: float = Field(
        default=6.0,
        ge=0.0,
        le=10.0,
        description="Minimum weighted average score to consider an interaction 'passing'.",
    )

    # ── SLA Benchmarks (2026 Targets) ───────────────────────────────────────
    SLA_ACCURACY: float = Field(
        default=0.98,
        description="Groundedness target — 98% accuracy.",
    )
    SLA_LATENCY_MS: float = Field(
        default=300.0,
        description="Maximum acceptable latency in milliseconds.",
    )
    SLA_MOS_SCORE: float = Field(
        default=4.3,
        description="Minimum Mean Opinion Score for voice quality.",
    )
    SLA_RESOLUTION_RATE: float = Field(
        default=0.80,
        description="Target autonomous resolution rate — 80%.",
    )

    # ── RCA ──────────────────────────────────────────────────────────────────
    RCA_CONFIDENCE_FLOOR: float = Field(
        default=0.5,
        description=(
            "ThoughtStep confidence below this value triggers a "
            "LOW_CONFIDENCE_CHAIN diagnostic."
        ),
    )
    RCA_LATENCY_SPIKE_MULTIPLIER: float = Field(
        default=2.0,
        description=(
            "Tool calls exceeding SLA_LATENCY_MS × this multiplier are "
            "flagged as LATENT_API_RESPONSE."
        ),
    )

    # ── Synchronization ─────────────────────────────────────────────────────
    PROJECT_ROOT: str = Field(
        default=".",
        description="Path to the InsightDesk-AI monorepo root for manifest watching.",
    )
    MANIFEST_FILENAMES: list[str] = Field(
        default=["phase1_manifest.json", "current_stage_manifest.json"],
        description="Manifest filenames to watch in the project root.",
    )

    # ── Core Intelligence Upstream ──────────────────────────────────────────
    CORE_INTELLIGENCE_URL: str = Field(
        default="http://localhost:8100",
        description="Base URL of the Core Intelligence service.",
    )

    model_config = {"env_prefix": "INFRA_", "env_file": ".env", "extra": "ignore"}


# ── Singleton ────────────────────────────────────────────────────────────────
settings = Settings()

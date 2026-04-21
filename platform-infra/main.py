# ──────────────────────────────────────────────────────────────────────────────
# InsightDesk AI — Platform Infrastructure Service
# The "Conscience and Memory" of the Quality Orchestration Platform.
#
# FastAPI application that exposes:
#   • Interaction Intelligence Repository (Memory)
#   • Judge Reliability Harness (JRH) multi-judge ensemble
#   • G-Eval with Chain-of-Thought evaluation
#   • Automated Root Cause Analysis (RCA)
#   • DAGMetric deterministic path validation
#   • Dashboard metrics aggregation
#
# This is the primary entry point for the platform-infra microservice.
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ── Resolve imports ─────────────────────────────────────────────────────────
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import settings
from src.db.engine import init_db, dispose_db
from src.evaluators.jrh_ensemble import JRHEnsemble
from src.evaluators.g_eval import GEvaluator
from src.diagnostics.rca_engine import RCAEngine
from src.metrics.dag_metric import DAGMetric
from src.metrics.aggregator import MetricsAggregator
from src.sync.manifest_watcher import ManifestWatcher

from src.routers import interactions, evaluation, diagnostics, metrics
from src.routers.evaluation import init_evaluators
from src.routers.diagnostics import init_diagnostics
from src.routers.metrics import init_metrics

# ── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-40s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("insightdesk.infra.main")

# ── Globals ─────────────────────────────────────────────────────────────────
_manifest_watcher: ManifestWatcher | None = None
_watcher_task: asyncio.Task | None = None


# ── Lifespan ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — initialize all subsystems."""
    global _manifest_watcher, _watcher_task

    # ── Database ─────────────────────────────────────────────────────────
    await init_db()

    # ── Evaluators ───────────────────────────────────────────────────────
    jrh = JRHEnsemble()
    g_eval = GEvaluator()
    init_evaluators(jrh, g_eval)
    logger.info("JRH ensemble initialized — %d judges", len(jrh.judges))

    # ── Diagnostics ──────────────────────────────────────────────────────
    rca = RCAEngine()
    init_diagnostics(rca)
    logger.info("RCA engine initialized")

    # ── Metrics ──────────────────────────────────────────────────────────
    dag = DAGMetric()
    agg = MetricsAggregator()
    init_metrics(dag, agg)
    logger.info("DAGMetric initialized — %d built-in DAGs", len(dag.list_dags()))

    # ── Manifest Watcher ─────────────────────────────────────────────────
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    _manifest_watcher = ManifestWatcher(project_root=project_root)

    def _on_manifest(filename, data):
        new_dags = data.get("dag_definitions", {})
        for name, dag_info in new_dags.items():
            steps = dag_info.get("steps", [])
            parsed_dag = []
            prev_node = None
            for step in steps:
                parsed_dag.append((step, [prev_node] if prev_node else []))
                prev_node = step
            dag.register_dag(name, parsed_dag)

    _manifest_watcher.on_manifest_change(_on_manifest)

    # Check for manifests at startup
    startup_manifest = _manifest_watcher.check_once()
    if startup_manifest:
        _on_manifest("startup", startup_manifest)

    # Start background watcher
    _watcher_task = asyncio.create_task(_manifest_watcher.start(poll_interval_seconds=30.0))

    logger.info("══════════════════════════════════════════════════════════════")
    logger.info("  InsightDesk AI — Platform Infrastructure Service ONLINE")
    logger.info("  Memory: SQL │ JRH: 3-Judge │ RCA: Active │ DAG: %d paths", len(dag.list_dags()))
    logger.info("  SLA Targets: Accuracy≥%.0f%% │ Latency≤%.0fms │ Resolution≥%.0f%%",
                settings.SLA_ACCURACY * 100, settings.SLA_LATENCY_MS, settings.SLA_RESOLUTION_RATE * 100)
    logger.info("══════════════════════════════════════════════════════════════")

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────
    if _manifest_watcher:
        await _manifest_watcher.stop()
    if _watcher_task:
        _watcher_task.cancel()
    await dispose_db()
    logger.info("Platform Infrastructure Service shutdown complete.")


# ── FastAPI App ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="InsightDesk AI — Platform Infrastructure",
    description=(
        "The 'Conscience and Memory' of InsightDesk AI. "
        "Manages the Interaction Intelligence Repository, JRH multi-judge ensemble, "
        "G-Eval/DAGMetric evaluation frameworks, and Automated Root Cause Analysis."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount Routers ───────────────────────────────────────────────────────────
app.include_router(interactions.router)
app.include_router(evaluation.router)
app.include_router(diagnostics.router)
app.include_router(metrics.router)


# ── Health & Status ─────────────────────────────────────────────────────────

@app.get("/", tags=["Status"])
async def root():
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "status": "operational",
        "capabilities": [
            "interaction_repository",
            "jrh_multi_judge_ensemble",
            "g_eval_chain_of_thought",
            "dag_metric_validation",
            "automated_rca",
            "shift_left_regression",
            "manifest_sync",
        ],
    }


@app.get("/health", tags=["Status"])
async def health_check():
    return {
        "status": "healthy",
        "sla_targets": {
            "accuracy": settings.SLA_ACCURACY,
            "latency_ms": settings.SLA_LATENCY_MS,
            "resolution_rate": settings.SLA_RESOLUTION_RATE,
            "mos_score": settings.SLA_MOS_SCORE,
        },
    }

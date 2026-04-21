# Platform Infrastructure — Reliability & Intelligence Backbone

**Lead**: Strategic AI Architect  
**Status**: Feature-Complete

The "Conscience and Memory" of the InsightDesk AI Quality Orchestration Platform. This service captures, evaluates, diagnoses, and validates every interaction produced by the Core Intelligence service.

---

## Architecture

```
platform-infra/
├── main.py                    ← FastAPI entrypoint (all routers mounted)
├── src/
│   ├── config.py              ← Centralized settings (DB, judges, SLA targets)
│   ├── db/                    ← Interaction Intelligence Repository
│   │   ├── engine.py          ← Async SQLAlchemy engine (PostgreSQL/SQLite)
│   │   ├── models.py          ← ORM: interaction_log, judge_verdict, rca_trace
│   │   └── repository.py     ← CRUD operations + aggregate queries
│   ├── evaluators/            ← Judge Reliability Harness (JRH)
│   │   ├── judge_models.py    ← Abstract BaseJudge + OpenAI/Anthropic/Gemini
│   │   ├── jrh_ensemble.py    ← Multi-judge consensus with entropy gating
│   │   └── g_eval.py          ← G-Eval with Chain-of-Thought scoring
│   ├── diagnostics/           ← Automated Root Cause Analysis
│   │   ├── failure_classifier.py  ← 6-category failure taxonomy
│   │   └── rca_engine.py      ← Tracing agent with NL explanations
│   ├── metrics/               ← Advanced Metrics
│   │   ├── dag_metric.py      ← DAGMetric deterministic path validation
│   │   └── aggregator.py      ← Dashboard KPIs (Hallucination Index, etc.)
│   ├── sync/                  ← Synchronization
│   │   └── manifest_watcher.py  ← Watches for Core AI phase manifests
│   └── routers/               ← API Layer
│       ├── interactions.py    ← /interactions/* (ingest, query, detail)
│       ├── evaluation.py      ← /evaluate/* (JRH, G-Eval, verdicts)
│       ├── diagnostics.py     ← /diagnostics/* (RCA, traces, batch)
│       └── metrics.py         ← /metrics/* (dashboard, DAG, trends)
```

## 2026 Performance Benchmarks (SLA Targets)

| Metric | Target | Enforcement |
|---|---|---|
| **Accuracy** | ≥ 98% | `accuracy_score` on every interaction |
| **Latency** | ≤ 300ms | `total_latency_ms` tracking |
| **Resolution Rate** | ≥ 80% | `autonomous_resolution` flag |
| **Voice MOS** | ≥ 4.3/5 | Voice session telemetry |
| **Hallucination Rate** | ≤ 2% | `hallucination_flag` index |

## Key Mechanisms

### Judge Reliability Harness (JRH)
- **3 independent judges** from different providers (OpenAI, Anthropic, Google)
- **Position rotation** to prevent first-response bias
- **Shannon entropy** gating — high disagreement routes to human calibration
- **Confidence-weighted** composite scoring

### Root Cause Analysis (RCA)
- **6-category failure taxonomy**: malformed tool call, retrieval failure, latent API, hallucination, low confidence, voice degradation
- **Natural-language explanations** for every diagnostic
- **Shift-left regression**: auto-generates test templates from failures

### DAGMetric
- **Deterministic path validation** for high-stakes operations
- **Built-in DAGs**: billing, subscription, refund, account deletion
- **Topological order** and **completeness** scoring

## Quick Start

```bash
cd platform-infra
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

API docs: `http://localhost:8001/docs`

## Schema Synchronization

This service consumes schemas from `/shared/schemas/`:
- `reasoning.py` → `AgentExecutionState`, `ThoughtStep`, `ToolInvocation`
- `mcp.py` → `CallToolResult`, `ContentBlock`
- `voice.py` → `VoiceSession`, `AudioChunk`
- `self_healing.py` → `HealingReport`, `TestJourney`

The manifest watcher monitors the project root for `phase1_manifest.json` or `current_stage_manifest.json` to auto-calibrate when the Core AI deploys new capabilities.

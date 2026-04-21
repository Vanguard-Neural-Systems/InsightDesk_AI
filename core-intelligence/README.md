# Core Intelligence — "Mind and High-Speed Body"

**Lead**: Core AI & Systems Architect

The central nervous system of InsightDesk AI. This microservice implements the three pillars of the 2026-tier Quality Orchestration platform:

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Gateway (main.py)                     │
├──────────────┬──────────────────┬───────────────────────────────┤
│  /reasoning  │     /voice       │         /healing              │
├──────────────┼──────────────────┼───────────────────────────────┤
│  engine.py   │ voice_handler.py │      self_healing.py          │
│  RAGless     │ WebRTC / UDP     │    Vision AI + StepIQ         │
│  Think→Act→  │ TTFA < 300ms     │    Element Fingerprinting     │
│  Observe     │ Barge-in AEC     │    Auto Patch + Validate      │
├──────────────┴──────────────────┴───────────────────────────────┤
│                  mcp_client.py — MCP Registry                   │
│             "USB-C for Data" · JSON-RPC 2.0 · SQL + Notion      │
├─────────────────────────────────────────────────────────────────┤
│           shared/schemas/ — Single Source of Truth              │
│        mcp.py · reasoning.py · voice.py · self_healing.py       │
└─────────────────────────────────────────────────────────────────┘
```

## Modules

| File | Role | Key Tech |
|------|------|----------|
| `main.py` | FastAPI app, endpoint routing, lifespan management | FastAPI, CORS |
| `engine.py` | RAGless reasoning: Think → Act → Observe → Self-Correct | MCP tools, CoT |
| `voice_handler.py` | WebRTC voice pipeline with barge-in detection | aiortc, UDP |
| `self_healing.py` | Autonomous test journey repair via drift detection | Vision AI, StepIQ |
| `mcp_client.py` | JSON-RPC 2.0 client for MCP tool/resource access | httpx, JSON-RPC |

## 2026 Performance Benchmarks

| Metric | Target | How |
|--------|--------|-----|
| **Autonomous Resolution** | 80% | RAGless reasoning + MCP tool execution |
| **Accuracy** | 98% groundedness | Tool-grounded answers, near-zero hallucination |
| **Voice TTFA** | < 300 ms | WebRTC over UDP, no head-of-line blocking |
| **Voice MOS** | ≥ 4.3 / 5 | Native audio reasoning (Gemini 2.0 Flash) |
| **QA Maintenance** | 85% reduction | Self-healing auto-patches |
| **Throughput** | 42-50 t/s (local) | Apple M5 Pro optimized inference |

## Quick Start

```bash
cd core-intelligence
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## API Endpoints

### Reasoning
- `POST /reasoning/resolve` — Submit a query for autonomous resolution
- `POST /reasoning/tool` — Direct MCP tool invocation
- `GET  /reasoning/tools` — List available MCP tools

### Voice
- `POST /voice/offer` — Initiate WebRTC session (SDP offer/answer)
- `POST /voice/ice-candidate` — Add trickle ICE candidate
- `GET  /voice/session/{id}` — Session telemetry (TTFA, MOS, jitter)

### Self-Healing
- `POST /healing/journeys` — Register a test journey
- `GET  /healing/journeys` — List all journeys + health status
- `POST /healing/heal` — Trigger self-healing cycle
- `GET  /healing/stats` — Aggregate healing metrics

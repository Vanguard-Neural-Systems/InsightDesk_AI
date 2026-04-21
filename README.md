# InsightDesk AI

> **2026-Tier Quality Orchestration Platform** — From reactive RAG bots to proactive, reasoning-based autonomous agents.

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=next.js&logoColor=white)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)

---

## Architecture

```
InsightDesk_AI/
├── core-intelligence/     ← Mind & Body — Reasoning, Voice, Self-Healing
│   ├── engine.py          ← RAGless Think→Act→Observe→Self-Correct loop
│   ├── voice_handler.py   ← WebRTC voice pipeline (TTFA <300ms)
│   ├── self_healing.py    ← Autonomous test journey repair
│   ├── mcp_client.py      ← JSON-RPC 2.0 MCP tool access
│   └── mock_mcp_server.py ← Development MCP tool simulator
│
├── platform-infra/        ← Conscience & Memory — Eval, Diagnostics, Metrics
│   └── src/
│       ├── evaluators/    ← JRH 3-judge ensemble + G-Eval
│       ├── diagnostics/   ← RCA engine + failure taxonomy
│       ├── metrics/       ← DAGMetric + dashboard aggregation
│       ├── db/            ← SQLAlchemy interaction repository
│       └── routers/       ← REST API surface
│
├── web-client/            ← Command Center — Next.js 16 Dashboard
│   └── src/
│       ├── app/           ← Pages: Dashboard, Voice, QA, Diagnostics, Healing, Inference
│       ├── components/    ← Glassmorphic UI components
│       ├── hooks/         ← API polling + hardware detection hooks
│       └── lib/           ← TypeScript types + unified API client
│
├── shared/                ← Source of Truth — Pydantic schemas
│   └── schemas/           ← mcp.py, reasoning.py, voice.py, self_healing.py
│
└── phase1_manifest.json   ← DAG definitions for deterministic path validation
```

## Key Capabilities

| Pillar | Feature | Target |
|--------|---------|--------|
| **RAGless Reasoning** | Think→Act→Observe with MCP tools | 98% accuracy, ~0% hallucination |
| **Voice Intelligence** | WebRTC/UDP native audio reasoning | TTFA < 300ms, MOS ≥ 4.3 |
| **Self-Healing QA** | Autonomous element drift repair | 85% maintenance reduction |
| **Judge Reliability** | 3-judge ensemble (JRH) with entropy gating | Cross-provider consensus |
| **Root Cause Analysis** | 6-category failure taxonomy + shift-left tests | Auto-generated regression tests |
| **Edge Inference** | Apple M5 Pro local LLM judges | 42–50 t/s (Qwen 2.5 32B) |

## Quick Start

### 1. Core Intelligence (Port 8000)

```bash
cd core-intelligence
pip install -r requirements.txt
# Start MCP mock server first
python mock_mcp_server.py &
# Start reasoning engine
uvicorn main:app --reload --port 8000
```

### 2. Platform Infrastructure (Port 8001)

```bash
cd platform-infra
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

### 3. Web Client (Port 3000)

```bash
cd web-client
npm install
npm run dev
```

### 4. End-to-End Test

```bash
python test_live_reasoning.py
```

## Service Ports

| Service | Port | Docs |
|---------|------|------|
| Core Intelligence | `8000` | http://localhost:8000/docs |
| Mock MCP Server | `8100` | — |
| Platform Infrastructure | `8001` | http://localhost:8001/docs |
| Web Client (Frontend) | `3000` | http://localhost:3000 |

## Environment Variables

Each service reads from its own `.env` file. Refer to `.env` in each directory. **Do not commit real API keys.**

| Variable | Service | Purpose |
|----------|---------|---------|
| `GEMINI_API_KEY` | core-intelligence | Primary LLM provider |
| `GROQ_API_KEY` | core-intelligence | Fallback LLM provider |
| `MCP_SERVER_URL` | core-intelligence | MCP tool backend |
| `INFRA_JUDGE_*_API_KEY` | platform-infra | JRH judge providers |
| `INFRA_SLA_*` | platform-infra | SLA enforcement thresholds |

## License

Proprietary — InsightDesk AI © 2026. All rights reserved.

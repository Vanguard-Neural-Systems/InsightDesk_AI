# InsightDesk AI

> **2026-Tier Quality Orchestration Platform** — From reactive RAG bots to proactive, reasoning-based autonomous agents.

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=next.js&logoColor=white)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Netlify Status](https://img.shields.io/badge/Netlify-Ready-00C7B7?logo=netlify&logoColor=white)](https://netlify.com)

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

## 🚀 Cloud Deployment Guide (GitHub to Netlify)

InsightDesk AI is a full-stack platform. While the highly interactive **Web Client (Next.js)** is perfectly suited for edge deployment on Netlify, the **Python AI Engines** (`core-intelligence` and `platform-infra`) must be hosted on platforms that support long-running processes (like Render, Railway, or AWS EC2).

### Step 1: Deploy Python Backends (Render / Railway)
1. Deploy `core-intelligence` and `platform-infra` as separate Web Services on Render or Railway.
2. Ensure you set your `GEMINI_API_KEY` and other LLM keys in their respective environments.
3. Note down their public URLs (e.g., `https://insightdesk-core.onrender.com`).

### Step 2: Deploy Next.js Frontend to Netlify

The repository is pre-configured with a `netlify.toml` file to automatically build the `web-client` subfolder.

1. **Push your code to GitHub**: Ensure this entire repository is pushed to a GitHub repository.
2. **Log into Netlify**: Go to [Netlify](https://app.netlify.com) and click **"Add new site" > "Import an existing project"**.
3. **Connect GitHub**: Authorize GitHub and select your `InsightDesk_AI` repository.
4. **Configure Build Settings**: Netlify will automatically detect the `netlify.toml` file. Confirm the following settings:
   - **Base directory**: `web-client`
   - **Build command**: `npm run build`
   - **Publish directory**: `web-client/.next`
5. **Set Environment Variables**: Click on "Add environment variables" and inject the public URLs of your Python backends:
   - `NEXT_PUBLIC_CORE_INTELLIGENCE_URL` = `https://<your-core-backend-url>`
   - `NEXT_PUBLIC_PLATFORM_INFRA_URL` = `https://<your-infra-backend-url>`
6. **Deploy**: Click **"Deploy site"**. Netlify will build the Next.js Turbopack and deploy it globally to their edge network!

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

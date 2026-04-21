# Web Client — InsightDesk AI Command Center

> **Next.js 16 + Tailwind CSS** — Glassmorphic dark-mode dashboard for real-time Quality Orchestration.

## Features

| Page | Route | Description |
|------|-------|-------------|
| **Dashboard** | `/` | Live KPIs (accuracy, latency, hallucination), 7-day trends, recent interactions |
| **Voice Intelligence** | `/voice` | WebRTC session controls, TTFA gauge, audio waveform visualizer |
| **QA Playground** | `/qa-playground` | Noise injection engine (55–65 dB), affirmation cue injector, stress test results |
| **Diagnostics & RCA** | `/diagnostics` | Reasoning trace view, root cause analysis, JRH 3-judge verdict panel |
| **Self-Healing** | `/healing` | Test journey registry, visual healing maps, drift patch visualization |
| **Inference Hub** | `/inference` | Hardware detection, tokens/sec monitoring, model roster, cloud savings |

## Architecture

```
src/
├── app/                    ← Next.js App Router pages
│   ├── page.tsx            ← Dashboard
│   ├── voice/page.tsx      ← Voice Intelligence
│   ├── qa-playground/      ← Acoustic QA Playground
│   ├── diagnostics/        ← Diagnostics & RCA
│   ├── healing/            ← Self-Healing Engine
│   └── inference/          ← Local Inference Hub
├── components/
│   ├── ui/                 ← Sidebar, MetricCard, StatusBadge
│   ├── voice-dashboard/    ← TTFAGauge, AudioVisualizer, WebRTCControls
│   ├── qa-playground/      ← NoiseInjector, AffirmationCues, StressResults
│   └── diagnostics/        ← TraceView, RCADetail, HealingMap, JRHVerdictPanel
├── hooks/
│   ├── use-api.ts          ← Generic API hook with retry + polling
│   └── local-inference/    ← useHardwareDetect, useInferenceStatus
└── lib/
    ├── api-client.ts       ← Unified dual-backend API client
    └── types/              ← TypeScript mirrors of shared/schemas/
```

## Design System

- **Background**: Deep navy (`#0a0e1a`) with animated mesh gradient orbs
- **Cards**: Frosted glass with `backdrop-blur(16px)` and subtle border glow
- **Accents**: Electric Cyan (`#00f0ff`), Vivid Violet (`#a855f7`), Neon Green (`#22d3ee`)
- **Typography**: Inter (UI) + JetBrains Mono (metrics/code)

## 2026 Performance Targets

| Metric | Target |
|--------|--------|
| Accuracy display fidelity | 98% representation |
| Dashboard update latency | < 300ms |
| Local inference throughput | 42–50 t/s (M5 Pro) |

## Quick Start

```bash
npm install
npm run dev     # → http://localhost:3000
```

## Backend Dependencies

The frontend expects two services running:
- **Core Intelligence**: `http://localhost:8000` (Reasoning, Voice, Healing)
- **Platform Infrastructure**: `http://localhost:8001` (Evaluation, Diagnostics, Metrics)

Set via env vars `NEXT_PUBLIC_CORE_INTELLIGENCE_URL` and `NEXT_PUBLIC_PLATFORM_INFRA_URL`.

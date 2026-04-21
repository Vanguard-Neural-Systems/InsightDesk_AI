// ──────────────────────────────────────────────────────────────────────────────
// InsightDesk AI — Central API Client
// Namespaced methods for both core-intelligence and platform-infra services.
// ──────────────────────────────────────────────────────────────────────────────

import type { AgentExecutionState } from "./types/reasoning";
import type { SDPOffer, ICECandidate, VoiceSession } from "./types/voice";
import type {
  TestJourney,
  HealingReport,
  ElementFingerprint,
} from "./types/self-healing";
import type {
  InteractionRecord,
  InteractionDetail,
  EnsembleResult,
  RCATrace,
  DashboardMetrics,
  TrendDataPoint,
  DAGValidationResult,
} from "./types/evaluation";

// ── Configuration ───────────────────────────────────────────────────────────

const CORE_URL =
  process.env.NEXT_PUBLIC_CORE_INTELLIGENCE_URL ?? "http://localhost:8000";
const INFRA_URL =
  process.env.NEXT_PUBLIC_PLATFORM_INFRA_URL ?? "http://localhost:8001";

// ── Helpers ─────────────────────────────────────────────────────────────────

async function request<T>(
  baseUrl: string,
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = `${baseUrl}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${body || res.statusText}`);
  }

  return res.json();
}

function core<T>(path: string, options?: RequestInit) {
  return request<T>(CORE_URL, path, options);
}

function infra<T>(path: string, options?: RequestInit) {
  return request<T>(INFRA_URL, path, options);
}

// ── Reasoning Engine ────────────────────────────────────────────────────────

export const reasoning = {
  resolve(query: string) {
    return core<AgentExecutionState>("/reasoning/resolve", {
      method: "POST",
      body: JSON.stringify({ query }),
    });
  },

  listTools() {
    return core<{ tools: string[] }>("/reasoning/tools");
  },
};

// ── Voice ───────────────────────────────────────────────────────────────────

export const voice = {
  offer(sdp: string) {
    const offer: SDPOffer = { type: "offer", sdp };
    return core<{ session_id: string; answer: { type: string; sdp: string } }>(
      "/voice/offer",
      { method: "POST", body: JSON.stringify(offer) }
    );
  },

  addIceCandidate(sessionId: string, candidate: ICECandidate) {
    return core<{ status: string }>(
      `/voice/ice-candidate?session_id=${encodeURIComponent(sessionId)}`,
      { method: "POST", body: JSON.stringify(candidate) }
    );
  },

  getSession(sessionId: string) {
    return core<VoiceSession>(`/voice/session/${encodeURIComponent(sessionId)}`);
  },
};

// ── Self-Healing ────────────────────────────────────────────────────────────

export const healing = {
  registerJourney(journey: TestJourney) {
    return core<{ status: string; journey_id: string }>(
      "/healing/journeys",
      { method: "POST", body: JSON.stringify(journey) }
    );
  },

  listJourneys() {
    return core<TestJourney[]>("/healing/journeys");
  },

  heal(journeyId: string, currentFingerprints: ElementFingerprint[]) {
    return core<HealingReport>("/healing/heal", {
      method: "POST",
      body: JSON.stringify({
        journey_id: journeyId,
        current_fingerprints: currentFingerprints,
      }),
    });
  },

  getStats() {
    return core<{
      total_healing_runs: number;
      maintenance_reduction_pct: number;
      registered_journeys: number;
    }>("/healing/stats");
  },
};

// ── Interactions ────────────────────────────────────────────────────────────

export const interactions = {
  list(params?: {
    min_accuracy?: number;
    max_accuracy?: number;
    hallucination_only?: boolean;
    autonomous_only?: boolean;
    limit?: number;
    offset?: number;
  }) {
    const qs = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null) qs.set(k, String(v));
      });
    }
    const query = qs.toString();
    return infra<InteractionRecord[]>(
      `/interactions/${query ? `?${query}` : ""}`
    );
  },

  get(sessionId: string) {
    return infra<InteractionDetail>(
      `/interactions/${encodeURIComponent(sessionId)}`
    );
  },
};

// ── Evaluation ──────────────────────────────────────────────────────────────

export const evaluate = {
  jrh(sessionId: string) {
    return infra<EnsembleResult>("/evaluate/jrh", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId }),
    });
  },

  jrhDirect(data: {
    query: string;
    thought_chain?: Record<string, unknown>[];
    final_resolution?: string;
    tool_calls?: Record<string, unknown>[];
    generator_provider?: string;
  }) {
    return infra<EnsembleResult>("/evaluate/jrh/direct", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  gEval(sessionId: string) {
    return infra<Record<string, unknown>>("/evaluate/g-eval", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId }),
    });
  },

  getVerdicts(sessionId: string) {
    return infra<{
      session_id: string;
      composite_score: number | null;
      needs_calibration: boolean;
      verdicts: Array<{
        judge_provider: string;
        judge_model: string;
        score: number;
        reasoning: string;
        confidence: number;
        position_index: number;
      }>;
    }>(`/evaluate/verdicts/${encodeURIComponent(sessionId)}`);
  },
};

// ── Diagnostics ─────────────────────────────────────────────────────────────

export const diagnostics = {
  analyze(sessionId: string) {
    return infra<Record<string, unknown>>("/diagnostics/analyze", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId }),
    });
  },

  listTraces(params?: {
    failure_category?: string;
    severity?: string;
    limit?: number;
    offset?: number;
  }) {
    const qs = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null) qs.set(k, String(v));
      });
    }
    const query = qs.toString();
    return infra<RCATrace[]>(`/diagnostics/traces${query ? `?${query}` : ""}`);
  },

  batchAnalyze(accuracyThreshold?: number, limit?: number) {
    const qs = new URLSearchParams();
    if (accuracyThreshold !== undefined)
      qs.set("accuracy_threshold", String(accuracyThreshold));
    if (limit !== undefined) qs.set("limit", String(limit));
    const query = qs.toString();
    return infra<{
      analyzed_count: number;
      threshold: number;
      diagnostics: Record<string, unknown>[];
    }>(`/diagnostics/batch-analyze${query ? `?${query}` : ""}`, {
      method: "POST",
    });
  },
};

// ── Metrics ─────────────────────────────────────────────────────────────────

export const metrics = {
  dashboard(windowHours: number = 24) {
    return infra<DashboardMetrics>(
      `/metrics/dashboard?window_hours=${windowHours}`
    );
  },

  trends(windowHours: number = 168) {
    return infra<{
      window_hours: number;
      data_points: number;
      trends: TrendDataPoint[];
    }>(`/metrics/trends?window_hours=${windowHours}`);
  },

  dagValidate(sessionId: string, dagName: string) {
    return infra<DAGValidationResult>(
      `/metrics/dag-validate/${encodeURIComponent(
        sessionId
      )}?dag_name=${encodeURIComponent(dagName)}`
    );
  },

  listDags() {
    return infra<{ dags: string[] }>("/metrics/dags");
  },
};

// ── Health ──────────────────────────────────────────────────────────────────

export const health = {
  core() {
    return core<{ status: string; mcp_tools_available: number }>("/health");
  },

  infra() {
    return infra<{ status: string; sla_targets: Record<string, number> }>(
      "/health"
    );
  },
};

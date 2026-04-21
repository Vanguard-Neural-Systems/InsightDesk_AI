// ──────────────────────────────────────────────────────────────────────────────
// InsightDesk AI — Evaluation & Metrics Types
// Derived from platform-infra router response shapes.
// ──────────────────────────────────────────────────────────────────────────────

export interface JudgeScore {
  provider: string;
  model: string;
  score: number;
  reasoning: string;
  confidence: number;
  coherence: number;
  consistency: number;
  fluency: number;
  relevance: number;
  position_index: number;
}

export interface EnsembleResult {
  composite_score: number;
  judge_scores: JudgeScore[];
  needs_human_calibration: boolean;
  agreement_rate: number;
}

export interface JudgeVerdict {
  judge_provider: string;
  judge_model: string;
  score: number;
  reasoning: string;
  confidence: number;
  position_index: number;
  coherence_score?: number;
  consistency_score?: number;
  fluency_score?: number;
  relevance_score?: number;
}

export interface InteractionRecord {
  id: number;
  session_id: string;
  query: string;
  accuracy_score: number;
  hallucination_flag: boolean;
  autonomous_resolution: boolean;
  total_latency_ms: number;
  jrh_composite_score?: number | null;
  jrh_needs_calibration: boolean;
  created_at?: string | null;
}

export interface InteractionDetail {
  interaction: {
    id: number;
    session_id: string;
    query: string;
    steps: Record<string, unknown>[];
    tool_calls: Record<string, unknown>[];
    memory_tier_used: string;
    final_resolution?: string | null;
    autonomous_resolution: boolean;
    accuracy_score: number;
    hallucination_flag: boolean;
    total_latency_ms: number;
    jrh_composite_score?: number | null;
    jrh_needs_calibration: boolean;
    created_at?: string | null;
  };
  verdicts: JudgeVerdict[];
}

export interface RCATrace {
  id: number;
  interaction_id: number;
  failure_category: string;
  severity: string;
  failed_step_index?: number | null;
  failed_tool_name?: string | null;
  root_cause_explanation: string;
  recommended_action: string;
  regression_test_generated: boolean;
  created_at?: string | null;
}

export interface DashboardMetrics {
  total_interactions: number;
  avg_accuracy: number;
  avg_latency_ms: number;
  resolution_rate: number;
  hallucination_rate: number;
  avg_jrh_score: number | null;
}

export interface TrendDataPoint {
  date: string;
  count: number;
  avg_accuracy: number;
  avg_latency_ms: number;
  resolution_rate: number;
  hallucination_rate: number;
}

export interface DAGValidationResult {
  session_id: string;
  dag_name: string;
  valid: boolean;
  matched_path: string[];
  missing_steps: string[];
  extra_steps: string[];
  coverage_pct: number;
}

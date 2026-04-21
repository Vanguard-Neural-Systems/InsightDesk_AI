// ──────────────────────────────────────────────────────────────────────────────
// InsightDesk AI — Reasoning Schemas (TypeScript mirror)
// Source of truth: shared/schemas/reasoning.py
// ──────────────────────────────────────────────────────────────────────────────

export enum ActionType {
  TOOL_CALL = "tool_call",
  MEMORY_UPDATE = "memory_update",
  RESPONSE = "response",
  SELF_CORRECT = "self_correct",
}

export enum MemoryTier {
  WORKING = "working",
  EPISODIC = "episodic",
  PERSISTENT = "persistent",
}

export interface ThoughtStep {
  step_index: number;
  thinking: string;
  action_type: ActionType;
  action_input?: Record<string, unknown> | null;
  observation?: string | null;
  confidence: number;
  latency_ms?: number | null;
}

export interface ToolInvocation {
  tool_name: string;
  arguments: Record<string, unknown>;
  result?: unknown;
  success: boolean;
  error?: string | null;
  latency_ms: number;
}

export interface AgentExecutionState {
  session_id: string;
  query: string;
  steps: ThoughtStep[];
  tool_calls: ToolInvocation[];
  memory_tier_used: MemoryTier;
  generator_provider: string;
  generator_model: string;
  final_resolution?: string | null;
  autonomous_resolution: boolean;
  accuracy_score: number;
  hallucination_flag: boolean;
  total_latency_ms: number;
}

export interface ActionOutput {
  success: boolean;
  data?: unknown;
  error?: string | null;
  latency_ms: number;
}

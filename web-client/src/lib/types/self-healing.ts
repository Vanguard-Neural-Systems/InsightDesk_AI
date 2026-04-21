// ──────────────────────────────────────────────────────────────────────────────
// InsightDesk AI — Self-Healing Schemas (TypeScript mirror)
// Source of truth: shared/schemas/self_healing.py
// ──────────────────────────────────────────────────────────────────────────────

export enum ElementType {
  UI_BUTTON = "ui_button",
  UI_INPUT = "ui_input",
  UI_LINK = "ui_link",
  UI_TEXT = "ui_text",
  UI_IMAGE = "ui_image",
  API_ENDPOINT = "api_endpoint",
  API_FIELD = "api_field",
}

export enum StepAction {
  CLICK = "click",
  TYPE = "type",
  NAVIGATE = "navigate",
  ASSERT_VISIBLE = "assert_visible",
  ASSERT_TEXT = "assert_text",
  API_CALL = "api_call",
  WAIT = "wait",
}

export enum DriftType {
  SELECTOR_CHANGED = "selector_changed",
  ATTRIBUTE_CHANGED = "attribute_changed",
  ELEMENT_REMOVED = "element_removed",
  ELEMENT_RELOCATED = "element_relocated",
  API_SCHEMA_CHANGED = "api_schema_changed",
  API_PATH_CHANGED = "api_path_changed",
}

export interface ElementFingerprint {
  element_id: string;
  element_type: ElementType;
  selector?: string | null;
  api_path?: string | null;
  attributes: Record<string, unknown>;
  visual_embedding?: number[] | null;
  confidence: number;
}

export interface JourneyStep {
  step_index: number;
  action: StepAction;
  target: ElementFingerprint;
  input_value?: string | null;
  expected_outcome?: string | null;
}

export interface TestJourney {
  journey_id: string;
  name: string;
  description: string;
  steps: JourneyStep[];
  last_passed?: string | null;
  is_healthy: boolean;
}

export interface HealingPatch {
  step_index: number;
  drift_type: DriftType;
  old_fingerprint: ElementFingerprint;
  new_fingerprint: ElementFingerprint;
  confidence: number;
  reasoning: string;
}

export interface HealingReport {
  journey_id: string;
  patches: HealingPatch[];
  auto_applied: number;
  needs_review: number;
  journey_healed: boolean;
}

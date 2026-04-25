"use client";

import { useCallback, useState } from "react";
import { Search, Zap } from "lucide-react";
import { useApi } from "@/hooks/use-api";
import * as api from "@/lib/api-client";
import { TraceView } from "@/components/diagnostics/trace-view";
import { RCADetail } from "@/components/diagnostics/rca-detail";
import { JRHVerdictPanel } from "@/components/diagnostics/jrh-verdict-panel";
import { StatusBadge } from "@/components/ui/status-badge";
import type { RCATrace } from "@/lib/types/evaluation";
import type { ThoughtStep, ToolInvocation } from "@/lib/types/reasoning";

export default function DiagnosticsPage() {
  const [selectedTrace, setSelectedTrace] = useState<RCATrace | null>(null);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [filter, setFilter] = useState<{ category?: string; severity?: string }>({});

  const { data: traces, loading, refetch } = useApi({
    fetcher: useCallback(
      () => api.diagnostics.listTraces({ ...filter, limit: 50 }),
      [filter]
    ),
    pollInterval: 30000,
  });

  const { data: interactionDetail } = useApi({
    fetcher: useCallback(
      () => (selectedSessionId ? api.interactions.get(selectedSessionId) : Promise.resolve(null)),
      [selectedSessionId]
    ),
    immediate: !!selectedSessionId,
  });

  const { data: verdictData } = useApi({
    fetcher: useCallback(
      () => (selectedSessionId ? api.evaluate.getVerdicts(selectedSessionId) : Promise.resolve(null)),
      [selectedSessionId]
    ),
    immediate: !!selectedSessionId,
  });

  const handleBatchAnalyze = async () => {
    try {
      await api.diagnostics.batchAnalyze(0.98, 50);
      refetch();
    } catch (err) {
      console.error("Batch analyze failed:", err);
    }
  };

  const selectTrace = (trace: RCATrace) => {
    setSelectedTrace(trace);
    if (trace.session_id) {
      setSelectedSessionId(trace.session_id);
    } else {
      setSelectedSessionId(null);
    }
  };

  const categories = ["tool_call_failure", "retrieval_failure", "hallucination", "latency_violation", "low_confidence"];
  const severities = ["critical", "high", "medium", "low"];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)] flex items-center gap-3">
            <Search className="w-6 h-6 text-[var(--cyan)]" />
            Diagnostics & RCA
          </h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            Root Cause Analysis — Trace failures to their origin
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleBatchAnalyze}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-[var(--cyan)] to-[var(--violet)] text-white text-xs font-semibold hover:opacity-90 transition-opacity"
          >
            <Zap className="w-3.5 h-3.5" />
            Batch Analyze
          </button>
          <StatusBadge status="operational" label="RCA Engine" />
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <select
          value={filter.category ?? ""}
          onChange={(e) => setFilter((f) => ({ ...f, category: e.target.value || undefined }))}
          className="px-3 py-1.5 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-subtle)] text-xs text-[var(--text-secondary)] focus:border-[var(--border-active)] outline-none"
        >
          <option value="">All Categories</option>
          {categories.map((c) => (
            <option key={c} value={c}>{c.replace(/_/g, " ")}</option>
          ))}
        </select>
        <select
          value={filter.severity ?? ""}
          onChange={(e) => setFilter((f) => ({ ...f, severity: e.target.value || undefined }))}
          className="px-3 py-1.5 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-subtle)] text-xs text-[var(--text-secondary)] focus:border-[var(--border-active)] outline-none"
        >
          <option value="">All Severities</option>
          {severities.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <span className="text-[11px] text-[var(--text-muted)]">
          {traces?.length ?? 0} traces
        </span>
      </div>

      {/* Split View */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Trace List */}
        <div className="glass-card-static p-4 max-h-[600px] overflow-y-auto">
          <h3 className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-3">
            RCA Traces
          </h3>
          {loading && !traces ? (
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="shimmer h-16 rounded-lg" />
              ))}
            </div>
          ) : traces && traces.length > 0 ? (
            <div className="space-y-2">
              {traces.map((t) => {
                const sevColor: Record<string, string> = {
                  critical: "text-[var(--red)]",
                  high: "text-[var(--amber)]",
                  medium: "text-[var(--violet)]",
                  low: "text-[var(--cyan)]",
                };
                return (
                  <button
                    key={t.id}
                    onClick={() => selectTrace(t)}
                    className={`w-full text-left p-3 rounded-lg border transition-all ${
                      selectedTrace?.id === t.id
                        ? "bg-[var(--cyan-glow)] border-[var(--border-active)]"
                        : "bg-[var(--bg-surface)] border-[var(--border-subtle)] hover:border-[var(--border-glass)]"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] font-medium text-[var(--text-primary)]">
                        {t.failure_category.replace(/_/g, " ")}
                      </span>
                      <span className={`text-[10px] font-bold uppercase ${sevColor[t.severity] ?? ""}`}>
                        {t.severity}
                      </span>
                    </div>
                    <p className="text-[10px] text-[var(--text-muted)] line-clamp-1">
                      {t.root_cause_explanation}
                    </p>
                  </button>
                );
              })}
            </div>
          ) : (
            <p className="text-xs text-[var(--text-muted)] text-center py-8">
              No RCA traces found. Run Batch Analyze to generate diagnostics.
            </p>
          )}
        </div>

        {/* Detail Panel */}
        <div className="xl:col-span-2 space-y-6">
          <RCADetail trace={selectedTrace} />

          {/* Reasoning Trace */}
          {interactionDetail?.interaction?.steps && (
            <div className="glass-card-static p-6">
              <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-4">
                Reasoning Trace
              </h3>
              <TraceView
                steps={interactionDetail.interaction.steps as unknown as ThoughtStep[]}
                toolCalls={interactionDetail.interaction.tool_calls as unknown as ToolInvocation[]}
                failedStepIndex={selectedTrace?.failed_step_index}
                rcaExplanation={selectedTrace?.root_cause_explanation}
              />
            </div>
          )}

          {/* JRH Verdicts */}
          {verdictData?.verdicts && (
            <JRHVerdictPanel
              verdicts={verdictData.verdicts}
              compositeScore={verdictData.composite_score}
              needsCalibration={verdictData.needs_calibration}
            />
          )}
        </div>
      </div>
    </div>
  );
}

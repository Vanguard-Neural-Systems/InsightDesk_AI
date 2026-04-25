"use client";

import { useCallback, useEffect } from "react";
import {
  Activity,
  Brain,
  Shield,
  Timer,
  Mic,
  BarChart3,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  Trash2,
} from "lucide-react";
import { MetricCard } from "@/components/ui/metric-card";
import { StatusBadge } from "@/components/ui/status-badge";
import { LiveSandbox } from "@/components/dashboard/live-sandbox";
import { useApi } from "@/hooks/use-api";
import * as api from "@/lib/api-client";
import type { InteractionRecord, TrendDataPoint } from "@/lib/types/evaluation";

export default function DashboardPage() {
  const { data: dashboardData, loading: dashLoading, refetch: refetchDashboard } = useApi({
    fetcher: useCallback(() => api.metrics.dashboard(24), []),
    pollInterval: 15000,
  });

  const { data: trendData, refetch: refetchTrends } = useApi({
    fetcher: useCallback(() => api.metrics.trends(168), []),
    pollInterval: 60000,
  });

  const { data: recentInteractions, refetch: refetchInteractions } = useApi({
    fetcher: useCallback(() => api.interactions.list({ limit: 8 }), []),
    pollInterval: 10000,
  });

  const { data: coreHealth } = useApi({
    fetcher: useCallback(() => api.health.core(), []),
    pollInterval: 30000,
  });

  const { data: infraHealth } = useApi({
    fetcher: useCallback(() => api.health.infra(), []),
    pollInterval: 30000,
  });

  const handleResetData = async () => {
    try {
      await api.interactions.deleteAll();
      refetchDashboard();
      refetchTrends();
      refetchInteractions();
    } catch (e) {
      console.error("Failed to reset data", e);
    }
  };

  // Listen for refresh events
  useEffect(() => {
    const handleRefresh = () => {
      refetchDashboard();
      refetchTrends();
      refetchInteractions();
    };
    window.addEventListener("refreshDashboardData", handleRefresh);
    return () => window.removeEventListener("refreshDashboardData", handleRefresh);
  }, [refetchDashboard, refetchTrends, refetchInteractions]);

  const d = dashboardData;
  const trends = trendData?.trends ?? [];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">
            Command Center
          </h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            Quality Orchestration Overview — Live Metrics
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleResetData}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[var(--red)] text-[var(--red)] text-xs font-semibold hover:bg-[var(--red-glow)] transition-colors mr-2"
          >
            <Trash2 className="w-3.5 h-3.5" />
            Reset DB
          </button>
          <StatusBadge
            status={coreHealth?.status === "healthy" ? "operational" : "degraded"}
            label="Core Intelligence"
          />
          <StatusBadge
            status={infraHealth?.status === "healthy" ? "operational" : "degraded"}
            label="Platform Infra"
          />
        </div>
      </div>

      {/* KPI Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <MetricCard
          title="Resolution Rate"
          value={d ? Math.round(d.resolution_rate.value * 100) : 0}
          unit="%"
          status={
            d
              ? d.resolution_rate.value >= 0.8
                ? "healthy"
                : d.resolution_rate.value >= 0.6
                ? "warning"
                : "critical"
              : "neutral"
          }
          trend="up"
          trendValue="Target: 80%"
          icon={<Brain className="w-4 h-4" />}
        />
        <MetricCard
          title="Accuracy"
          value={d ? (d.accuracy.avg_score * 100).toFixed(1) : "0"}
          unit="%"
          status={
            d
              ? d.accuracy.avg_score >= 0.98
                ? "healthy"
                : d.accuracy.avg_score >= 0.9
                ? "warning"
                : "critical"
              : "neutral"
          }
          trend="up"
          trendValue="Target: 98%"
          icon={<Shield className="w-4 h-4" />}
        />
        <MetricCard
          title="Hallucination Index"
          value={d ? (d.hallucination_index.value * 100).toFixed(2) : "0"}
          unit="%"
          status={
            d
              ? d.hallucination_index.value <= 0.02
                ? "healthy"
                : d.hallucination_index.value <= 0.05
                ? "warning"
                : "critical"
              : "neutral"
          }
          trend="down"
          trendValue="Target: ~0%"
          icon={<AlertTriangle className="w-4 h-4" />}
        />
        <MetricCard
          title="Avg Latency"
          value={d ? Math.round(d.latency.avg_ms) : 0}
          unit="ms"
          status={
            d
              ? d.latency.avg_ms <= 300
                ? "healthy"
                : d.latency.avg_ms <= 500
                ? "warning"
                : "critical"
              : "neutral"
          }
          trend="down"
          trendValue="Target: <300ms"
          icon={<Timer className="w-4 h-4" />}
        />
        <MetricCard
          title="JRH Agreement"
          value={d?.jrh.agreement_rate ? (d.jrh.agreement_rate * 100).toFixed(1) : "N/A"}
          unit={d?.jrh.agreement_rate ? "%" : ""}
          status={
            d?.jrh.agreement_rate
              ? d.jrh.agreement_rate >= 0.85
                ? "healthy"
                : "warning"
              : "neutral"
          }
          icon={<BarChart3 className="w-4 h-4" />}
        />
        <MetricCard
          title="Total Interactions"
          value={d?.total_interactions ?? 0}
          status="neutral"
          trend="up"
          icon={<Activity className="w-4 h-4" />}
        />
      </div>

      {/* Live Worker Sandbox - Real-time Audit Testing */}
      <LiveSandbox />

      {/* Trend Visualization + Recent Interactions */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Trend Chart */}
        <div className="xl:col-span-2 glass-card-static p-6">
          <h2 className="text-sm font-semibold text-[var(--text-primary)] mb-4 flex items-center gap-2">
            <Activity className="w-4 h-4 text-[var(--cyan)]" />
            7-Day Trend
          </h2>

          {trends.length > 0 ? (
            <div className="space-y-4">
              {/* Accuracy trend bars */}
              <div>
                <p className="text-xs text-[var(--text-muted)] mb-2 uppercase tracking-wider">
                  Accuracy per Day
                </p>
                <div className="flex items-end gap-2 h-24">
                  {trends.map((t: TrendDataPoint, i: number) => {
                    const pct = t.avg_accuracy * 100;
                    const color =
                      pct >= 98
                        ? "bg-[var(--green)]"
                        : pct >= 90
                        ? "bg-[var(--amber)]"
                        : "bg-[var(--red)]";
                    return (
                      <div
                        key={i}
                        className="flex-1 flex flex-col items-center gap-1"
                      >
                        <span className="text-[10px] text-[var(--text-muted)] font-mono">
                          {pct.toFixed(0)}%
                        </span>
                        <div
                          className={`w-full rounded-t-sm ${color} transition-all duration-500`}
                          style={{
                            height: `${Math.max(pct * 0.9, 4)}%`,
                            opacity: 0.85,
                          }}
                        />
                        <span className="text-[9px] text-[var(--text-muted)]">
                          {t.date.slice(5)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Latency trend bars */}
              <div>
                <p className="text-xs text-[var(--text-muted)] mb-2 uppercase tracking-wider">
                  Avg Latency (ms)
                </p>
                <div className="flex items-end gap-2 h-20">
                  {trends.map((t: TrendDataPoint, i: number) => {
                    const maxLat = Math.max(
                      ...trends.map((x: TrendDataPoint) => x.avg_latency_ms),
                      1
                    );
                    const pct = (t.avg_latency_ms / maxLat) * 100;
                    const color =
                      t.avg_latency_ms <= 300
                        ? "bg-[var(--cyan)]"
                        : t.avg_latency_ms <= 500
                        ? "bg-[var(--amber)]"
                        : "bg-[var(--red)]";
                    return (
                      <div
                        key={i}
                        className="flex-1 flex flex-col items-center gap-1"
                      >
                        <span className="text-[10px] text-[var(--text-muted)] font-mono">
                          {Math.round(t.avg_latency_ms)}
                        </span>
                        <div
                          className={`w-full rounded-t-sm ${color} transition-all duration-500`}
                          style={{
                            height: `${Math.max(pct * 0.85, 4)}%`,
                            opacity: 0.75,
                          }}
                        />
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-40 text-[var(--text-muted)] text-sm">
              {dashLoading ? (
                <div className="shimmer w-full h-full rounded-lg" />
              ) : (
                "No trend data available yet. Ingest interactions to see trends."
              )}
            </div>
          )}
        </div>

        {/* Recent Interactions */}
        <div className="glass-card-static p-6 max-h-[480px] overflow-y-auto">
          <h2 className="text-sm font-semibold text-[var(--text-primary)] mb-4 flex items-center gap-2">
            <Clock className="w-4 h-4 text-[var(--violet)]" />
            Recent Interactions
          </h2>

          {recentInteractions && recentInteractions.length > 0 ? (
            <div className="space-y-3">
              {recentInteractions.map((item: InteractionRecord) => (
                <div
                  key={item.id}
                  className="p-3 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-subtle)] hover:border-[var(--border-active)] transition-all cursor-pointer"
                >
                  <div className="flex items-start justify-between mb-1.5">
                    <p className="text-xs font-medium text-[var(--text-primary)] line-clamp-1 flex-1 mr-2">
                      {item.query}
                    </p>
                    {item.autonomous_resolution ? (
                      <CheckCircle className="w-3.5 h-3.5 text-[var(--green)] flex-shrink-0" />
                    ) : (
                      <XCircle className="w-3.5 h-3.5 text-[var(--amber)] flex-shrink-0" />
                    )}
                  </div>
                  <div className="flex items-center gap-3 text-[10px] text-[var(--text-muted)]">
                    <span className="font-mono">
                      {(item.accuracy_score * 100).toFixed(1)}% acc
                    </span>
                    <span className="font-mono">
                      {Math.round(item.total_latency_ms)}ms
                    </span>
                    {item.hallucination_flag && (
                      <span className="text-[var(--red)] font-semibold">
                        HALLUCINATION
                      </span>
                    )}
                    {item.jrh_composite_score !== null &&
                      item.jrh_composite_score !== undefined && (
                        <span className="font-mono">
                          JRH: {(item.jrh_composite_score * 100).toFixed(0)}%
                        </span>
                      )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-[var(--text-muted)] text-center py-8">
              No interactions recorded yet.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

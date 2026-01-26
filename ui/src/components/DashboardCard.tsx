import type { Dispatch, SetStateAction } from "react";
import type { Metric } from "../types";
import { Card } from "./Card";
import { MetricsTable } from "./MetricsTable";
import { Sparkline } from "./Sparkline";

type CriticalItem = {
  id: string;
  flags: string[];
  state: string;
};

type WeekSeries = {
  label: string;
  values: number[];
  color: string;
};

type PrSegment = {
  label: string;
  value: number;
  color: string;
};

type DashboardCardProps = {
  selectedTeamId: number | null;
  repoLabels: string;
  healthTone: string;
  prTotal: number;
  prSegments: PrSegment[];
  prTotalForMeter: number;
  latestMetric: (name: string) => number | null;
  formatNumber: (value: number | null, digits?: number) => string;
  criticalPrs: CriticalItem[];
  criticalIssues: CriticalItem[];
  prHref: (id: string) => string | null;
  flagLabel: (flag: string) => string;
  weekSeries: WeekSeries[];
  showMetricsHistory: boolean;
  setShowMetricsHistory: Dispatch<SetStateAction<boolean>>;
  recentMetrics: Metric[];
  latestMetrics: Metric[];
};

export function DashboardCard({
  selectedTeamId,
  repoLabels,
  healthTone,
  prTotal,
  prSegments,
  prTotalForMeter,
  latestMetric,
  formatNumber,
  criticalPrs,
  criticalIssues,
  prHref,
  flagLabel,
  weekSeries,
  showMetricsHistory,
  setShowMetricsHistory,
  recentMetrics,
  latestMetrics,
}: DashboardCardProps) {
  return (
    <Card
      title="Dashboard"
      right={
        <span className="muted small">
          {selectedTeamId ? `Team #${selectedTeamId}` : ""}
          {repoLabels ? ` · ${repoLabels}` : ""}
        </span>
      }
      className={`card-health ${healthTone}`}
    >
      <div className="widget-grid">
        <div className="widget widget-blue">
          <div className="widget-title">PR state mix</div>
          <div className="widget-value">{formatNumber(prTotal, 0)} total</div>
          <div className="meter">
            {prSegments.map((seg) => (
              <span
                key={seg.label}
                style={{
                  width: `${Math.round((seg.value / prTotalForMeter) * 100)}%`,
                  background: seg.color,
                }}
              />
            ))}
          </div>
          <div className="legend">
            {prSegments.map((seg) => (
              <div key={seg.label} className="legend-item">
                <span className="legend-dot" style={{ background: seg.color }} />
                {seg.label} <strong>{Math.round(seg.value)}</strong>
              </div>
            ))}
          </div>
        </div>

        <div className="widget widget-rose">
          <div className="widget-title">Review coverage</div>
          <div className="widget-value">
            {formatNumber(latestMetric("pr_low_review_coverage_count"), 0)}
          </div>
          <div className="widget-sub">Open PRs &gt;24h without review</div>
        </div>

        <div className="widget widget-blue">
          <div className="widget-title">Jira blocked rate</div>
          <div className="widget-value">
            {formatNumber((latestMetric("jira_blocked_rate") ?? 0) * 100, 0)}%
          </div>
          <div className="widget-sub">Issues flagged as blocked</div>
        </div>

        <div className="widget widget-amber">
          <div className="widget-title">Critical PRs</div>
          <div className="critical-list">
            {criticalPrs.length ? criticalPrs.map((pr) => {
              const href = prHref(pr.id);
              return (
                <div key={pr.id} className="critical-item">
                  {href ? (
                    <a href={href} target="_blank" rel="noreferrer">
                      {pr.id}
                    </a>
                  ) : (
                    <span>{pr.id}</span>
                  )}
                  <span className="critical-meta">
                    {pr.flags.map(flagLabel).join(", ")}
                  </span>
                </div>
              );
            }) : <div className="muted small">No critical PRs in context.</div>}
          </div>
        </div>

        <div className="widget widget-rose">
          <div className="widget-title">Critical Issues</div>
          <div className="critical-list">
            {criticalIssues.length ? criticalIssues.map((issue) => (
              <div key={issue.id} className="critical-item">
                <span>{issue.id}</span>
                <span className="critical-meta">
                  {issue.flags.length ? issue.flags.map(flagLabel).join(", ") : issue.state}
                </span>
              </div>
            )) : <div className="muted small">No critical issues in context.</div>}
          </div>
        </div>
      </div>

      <hr className="soft" />

      <div className="grid week-metrics-grid">
        <div className="widget">
          <div className="widget-title">Week over week</div>
          <div className="spark-grid">
            {weekSeries.map((series) => {
              const values = series.values;
              const latest = values[values.length - 1];
              const prev = values[values.length - 2];
              const delta = Number.isFinite(latest) && Number.isFinite(prev) ? latest - prev : null;
              const deltaClass = delta == null || delta === 0 ? "delta neutral" : delta > 0 ? "delta up" : "delta down";
              return (
                <div className="spark-row" key={series.label}>
                  <div>
                    <div className="spark-label">{series.label}</div>
                    <div className="spark-value">{formatNumber(latest ?? null, 1)}</div>
                  </div>
                  <Sparkline values={values} color={series.color} />
                  <div className={deltaClass}>
                    {delta == null ? "—" : `${delta >= 0 ? "+" : ""}${formatNumber(delta, 1)}`}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="widget">
          <div className="metrics-head">
            <div style={{ fontWeight: 900 }}>Latest snapshot metrics</div>
            <button
              className="link-btn"
              onClick={() => setShowMetricsHistory((v) => !v)}
            >
              {showMetricsHistory ? "Show less" : "Show last 7 days"}
            </button>
          </div>
          <MetricsTable metrics={showMetricsHistory ? recentMetrics : latestMetrics} />
        </div>
      </div>
    </Card>
  );
}

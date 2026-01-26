import { useEffect, useMemo, useState } from "react";
import type { Team, WeeklyPlan, Metric, GitPullRequestMap } from "../types";
import { getTeams, getLatestPlan, runWeeklyPlan, snapshotMetrics, syncGit, getLatestMetrics, getGitPullRequests, getLlmContextPreview } from "../api";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { PlanView } from "../components/PlanView";
import { MetricsTable } from "../components/MetricsTable";
import { metricLabel } from "../metrics";

type ContextEntity = {
  kind: "pr" | "issue";
  id: string;
  state: string;
  age_days?: number | null;
  size?: number | null;
  flags: string[];
};

const formatNumber = (value: number | null, digits = 1) => {
  if (value == null || !Number.isFinite(value)) return "—";
  if (Math.abs(value) >= 1000) return `${(value / 1000).toFixed(1)}k`;
  if (digits === 0) return `${Math.round(value)}`;
  return value.toFixed(digits);
};

const Sparkline = (props: { values: number[]; color: string }) => {
  const values = props.values.filter((v) => Number.isFinite(v));
  if (!values.length) return <div className="spark-empty">No data</div>;

  const width = 160;
  const height = 42;
  const padding = 6;
  const max = Math.max(...values);
  const min = Math.min(...values);
  const range = max - min || 1;

  const points = values.map((v, i) => {
    const x = padding + (i * (width - padding * 2)) / Math.max(values.length - 1, 1);
    const y = height - padding - ((v - min) / range) * (height - padding * 2);
    return `${x},${y}`;
  }).join(" ");

  const lastX = padding + ((values.length - 1) * (width - padding * 2)) / Math.max(values.length - 1, 1);
  const lastY = height - padding - ((values[values.length - 1] - min) / range) * (height - padding * 2);

  return (
    <svg className="sparkline" viewBox={`0 0 ${width} ${height}`}>
      <polyline
        fill="none"
        stroke={props.color}
        strokeWidth="2"
        strokeLinejoin="round"
        strokeLinecap="round"
        points={points}
      />
      <circle cx={lastX} cy={lastY} r="3.5" fill={props.color} />
    </svg>
  );
};

type Toast = { kind: "ok" | "error"; message: string } | null;

export default function Dashboard() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [teamId, setTeamId] = useState<number | null>(null);
  const [plan, setPlan] = useState<WeeklyPlan | null>(null);
  const [rawJson, setRawJson] = useState<string | null>(null);

  const [busy, setBusy] = useState<string | null>(null);
  const [toast, setToast] = useState<Toast>(null);
  const [metrics, setMetrics] = useState<Metric[]>([])
  const [prs, setPrs] = useState<GitPullRequestMap[] | null>(null);
  const [contextEntities, setContextEntities] = useState<ContextEntity[]>([]);
  const [llmContext, setLlmContext] = useState<string | null>(null);
  const [showLlmContext, setShowLlmContext] = useState(false);
  const [showMetricsHistory, setShowMetricsHistory] = useState(false);

  const selectedTeam = useMemo(() => teams.find(t => t.id === teamId) ?? null, [teams, teamId]);
  const metricsByName = useMemo(() => {
    const map: Record<string, Metric[]> = {};
    metrics.forEach((m) => {
      if (!map[m.name]) map[m.name] = [];
      map[m.name].push(m);
    });
    Object.values(map).forEach((list) => {
      list.sort((a, b) => new Date(a.as_of_date).getTime() - new Date(b.as_of_date).getTime());
    });
    return map;
  }, [metrics]);

  const latestMetric = (name: string) => {
    const list = metricsByName[name];
    if (!list || !list.length) return null;
    return list[list.length - 1].value;
  };

  const seriesFor = (name: string, limit = 8) => {
    const list = metricsByName[name] ?? [];
    const values = list.map((m) => m.value);
    return values.slice(Math.max(values.length - limit, 0));
  };

  const latestMetrics = useMemo(() => {
    const latest: Metric[] = [];
    Object.values(metricsByName).forEach((list) => {
      if (list.length) latest.push(list[list.length - 1]);
    });
    return latest.sort((a, b) => a.name.localeCompare(b.name));
  }, [metricsByName]);

  const recentMetrics = useMemo(() => {
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - 7);
    return metrics.filter((m) => new Date(m.as_of_date) >= cutoff);
  }, [metrics]);

  const loadTeamData = async (id: number) => {
    const p = await getLatestPlan(id);
    setPlan(p);
    setRawJson(p ? JSON.stringify(p, null, 2) : null);

    const ms = await getLatestMetrics(id);
    setMetrics(ms);

    const prs = await getGitPullRequests(id);
    setPrs(prs);

    try {
      const ctx = await getLlmContextPreview(id);
      setContextEntities(Array.isArray(ctx?.entities) ? ctx.entities : []);
    } catch {
      setContextEntities([]);
    }
  };

  useEffect(() => {
    (async () => {
      try {
        const t = await getTeams();
        setTeams(t);
        if (t.length && teamId == null) setTeamId(t[0].id);
      } catch (e: any) {
        setToast({ kind: "error", message: e?.message ?? String(e) });
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!teamId) return;
    loadTeamData(teamId).catch((e: any) => {
      setToast({ kind: "error", message: e?.message ?? String(e) });
    });
  }, [teamId]);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 10000);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const act = async (label: string, fn: () => Promise<any>) => {
    setBusy(label);
    setToast(null);
    try {
      await fn();
      setToast({ kind: "ok", message: `${label} complete` });

      if (teamId) {
        await loadTeamData(teamId);
      }

    } catch (e: any) {
      setToast({ kind: "error", message: e?.message ?? String(e) });
    } finally {
      setBusy(null);
    }
  };

  const prTotal = latestMetric("pr_count") ?? 0;
  const prOpen = latestMetric("pr_open_count") ?? 0;
  const prNeedsReview = latestMetric("pr_low_review_coverage_count") ?? 0;
  const prClosed = Math.max(0, prTotal - prOpen);
  const prOpenOther = Math.max(0, prOpen - prNeedsReview);
  const prSegments = [
    { label: "Needs review", value: prNeedsReview, color: "var(--accent-warn)" },
    { label: "Open", value: prOpenOther, color: "var(--accent-open)" },
    { label: "Closed", value: prClosed, color: "var(--accent-ok)" },
  ];
  const prTotalForMeter = prSegments.reduce((sum, s) => sum + s.value, 0) || 1;

  const weekSeries = useMemo(() => {
    const keys = Object.keys(metricsByName).sort();
    const palette = [
      "var(--accent-open)",
      "var(--accent-ok)",
      "var(--accent-warn)",
      "var(--accent-teal)",
      "var(--accent-rose)",
      "var(--accent-violet)",
      "var(--accent-sky)",
    ];
    return keys.map((name, idx) => ({
      label: metricLabel(name),
      color: palette[idx % palette.length],
      values: seriesFor(name),
    }));
  }, [metricsByName]);

  const blockedRate = latestMetric("jira_blocked_rate") ?? 0;
  const staleCount = latestMetric("pr_stale_count") ?? 0;
  const lowReviewCount = latestMetric("pr_low_review_coverage_count") ?? 0;
  const healthTone =
    blockedRate > 0.2 || staleCount > 5 || lowReviewCount > 5
      ? "bad"
      : blockedRate > 0.1 || staleCount > 2 || lowReviewCount > 2
        ? "warn"
        : "good";

  const criticalPrs = useMemo(() => {
    const list = contextEntities.filter((e) => e.kind === "pr");
    const score = (e: ContextEntity) => {
      let s = 0;
      if (e.flags.includes("stale_pr")) s += 3;
      if (e.flags.includes("needs_review")) s += 2;
      if (e.flags.includes("mega_pr")) s += 2;
      s += Math.min((e.age_days ?? 0) / 2, 5);
      return s;
    };
    return list
      .filter((e) => e.flags.some((f) => ["stale_pr", "needs_review", "mega_pr"].includes(f)))
      .sort((a, b) => score(b) - score(a))
      .slice(0, 5);
  }, [contextEntities]);

  const criticalIssues = useMemo(() => {
    const list = contextEntities.filter((e) => e.kind === "issue");
    const score = (e: ContextEntity) => {
      let s = 0;
      if (e.flags.includes("blocked")) s += 3;
      s += Math.min((e.age_days ?? 0) / 2, 5);
      return s;
    };
    return list.sort((a, b) => score(b) - score(a)).slice(0, 5);
  }, [contextEntities]);

  const prHref = (id: string) => {
    const num = Number(id.replace(/[^\d]/g, ""));
    if (!num || !prs) return null;
    for (const repo of prs) {
      if (repo.pull_requests.includes(num) && repo.web_base_url) {
        return `${repo.web_base_url.replace(/\/$/, "")}/${repo.owner}/${repo.repo}/pull/${num}`;
      }
    }
    return null;
  };

  const flagLabel = (flag: string) => {
    if (flag === "stale_pr") return "stale";
    if (flag === "needs_review") return "needs review";
    if (flag === "mega_pr") return "mega";
    if (flag === "blocked") return "blocked";
    return flag.replace(/_/g, " ");
  };

  return (
    <div className="container">
      <div className="header">
        <div>
          <div className="h1">EM-Aide</div>
          <div className="sub">
            Weekly EM brief generated from local delivery signals. No code, diffs, or ticket text is sent to the model.
          </div>
        </div>

        <div className="row">
          <select value={teamId ?? ""} onChange={(e) => setTeamId(Number(e.target.value))}>
            {teams.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
        </div>
      </div>

      {toast ? (
        <div className={`notice ${toast.kind === "error" ? "error" : "ok"}`} style={{ marginBottom: 14 }}>
          <strong>{toast.kind === "error" ? "Error" : "OK"}:</strong>{" "}
          <span>{toast.message}</span>
        </div>
      ) : null}

      <div className="row" style={{ marginBottom: 14 }}>
        <Button
          kind="secondary"
          label={busy === "Sync Git" ? "Syncing…" : "Sync Git now"}
          disabled={!teamId || !!busy}
          onClick={() => act("Sync Git", () => syncGit(teamId!))}
        />
        <Button
          kind="secondary"
          label={busy === "Snapshot metrics" ? "Snapshotting…" : "Snapshot metrics"}
          disabled={!teamId || !!busy}
          onClick={() => act("Snapshot metrics", () => snapshotMetrics(teamId!))}
        />
        <Button
          label={busy === "Run weekly plan" ? "Planning…" : "Run weekly plan"}
          disabled={!teamId || !!busy}
          onClick={() => act("Run weekly plan", () => runWeeklyPlan(teamId!))}
        />
        <Button
          kind="secondary"
          label={busy === "Preview LLM data" ? "Loading…" : "Preview LLM data"}
          disabled={!teamId || !!busy}
          onClick={() =>
            act("Preview LLM data", async () => {
              const ctx = await getLlmContextPreview(teamId!);
              setLlmContext(JSON.stringify(ctx, null, 2));
              setShowLlmContext(true);
              return ctx;
            })
          }
        />
      </div>

      <div className="grid grid-2">
        <Card
          title="Dashboard"
          right={
            <span className="muted small">
              {selectedTeam ? `Team #${selectedTeam.id}` : ""}
              {prs ? " · " + prs.map((repo) => `${repo.owner}/${repo.repo}`).join(", ") : ""}
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

            <div className="widget widget-amber">
              <div className="widget-title">Cycle time</div>
              <div className="widget-value">
                {formatNumber(latestMetric("pr_avg_cycle_hours"), 1)}h
              </div>
              <div className="widget-sub">Avg merge time for recent PRs</div>
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

          <div className="widget wide">
            <div className="widget-title">Week over week</div>
            <div className="spark-grid">
              {weekSeries.map((series) => {
                const values = series.values;
                const latest = values[values.length - 1];
                const prev = values[values.length - 2];
                const delta = Number.isFinite(latest) && Number.isFinite(prev) ? latest - prev : null;
                const deltaClass = delta == null ? "delta neutral" : delta >= 0 ? "delta up" : "delta down";
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

          <hr className="soft" />

        {showLlmContext ? (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.55)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 18,
        zIndex: 50
      }}
      onClick={() => setShowLlmContext(false)}
    >
      <div
        className="card"
        style={{ width: "min(1100px, 96vw)", maxHeight: "86vh", overflow: "auto" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="card-head">
          <div className="card-title">LLM data preview (sanitized payload)</div>
          <div className="row">
            <Button kind="secondary" label="Close" onClick={() => setShowLlmContext(false)} />
          </div>
        </div>

      <div className="muted small" style={{ marginTop: 8 }}>
        This is the exact JSON payload sent to the model. Prompts are not shown.
        </div>

        <pre
          style={{
            whiteSpace: "pre-wrap",
            marginTop: 12,
            padding: 12,
            borderRadius: 14,
            border: "1px solid rgba(255,255,255,0.08)",
            background: "rgba(0,0,0,0.25)"
          }}
        >
          {llmContext ?? "No context loaded."}
        </pre>
      </div>
    </div>
  ) : null}

          <div style={{ marginTop: 12 }}>
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

        </Card>

        <Card title="Weekly plan" right={plan ? <span className="muted small">Latest</span> : null}>
          {plan ? (
            <PlanView plan={plan} rawJson={rawJson} pull_requests={prs} />
          ) : (
            <div className="muted">
              No plan yet. Click <code>Run weekly plan</code>.
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

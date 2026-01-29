import { useEffect, useMemo, useState } from "react";
import type { Team, WeeklyPlan, Metric, GitPullRequestMap } from "../types";
import { getTeams, getLatestPlan, runWeeklyPlan, snapshotMetrics, syncGit, syncJira, getLatestMetrics, getGitPullRequests, getLlmContextPreview, getHealth } from "../api";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { DashboardCard } from "../components/DashboardCard";
import { PlanView } from "../components/PlanView";
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
  const [activeTab, setActiveTab] = useState<"dashboard" | "plan">("dashboard");
  const [environment, setEnvironment] = useState<string | null>(null);

  const selectedTeam = useMemo(() => teams.find(t => t.id === teamId) ?? null, [teams, teamId]);
  const canPreviewLlm = environment === "local" || environment === "dev";
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

  const loadTeamData = async (id: number, includePreview: boolean) => {
    const p = await getLatestPlan(id);
    setPlan(p);
    setRawJson(p ? JSON.stringify(p, null, 2) : null);

    const ms = await getLatestMetrics(id);
    setMetrics(ms);

    const prs = await getGitPullRequests(id);
    setPrs(prs);

    if (!includePreview) {
      setContextEntities([]);
      return;
    }

    try {
      const ctx = await getLlmContextPreview(id);
      setContextEntities(Array.isArray(ctx?.entities) ? ctx.entities : []);
    } catch {
      setContextEntities([]);
    }
  };

  useEffect(() => {
    (async () => {
      const [teamsRes, healthRes] = await Promise.allSettled([getTeams(), getHealth()]);
      if (teamsRes.status === "fulfilled") {
        setTeams(teamsRes.value);
        if (teamsRes.value.length && teamId == null) setTeamId(teamsRes.value[0].id);
      } else {
        setToast({ kind: "error", message: teamsRes.reason?.message ?? String(teamsRes.reason) });
      }
      if (healthRes.status === "fulfilled") {
        setEnvironment(healthRes.value.environment ?? null);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!teamId) return;
    loadTeamData(teamId, canPreviewLlm).catch((e: any) => {
      setToast({ kind: "error", message: e?.message ?? String(e) });
    });
  }, [teamId, canPreviewLlm]);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 10000);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const act = async (label: string, fn: () => Promise<any>, onSuccess?: () => void) => {
    setBusy(label);
    setToast(null);
    try {
      await fn();
      setToast({ kind: "ok", message: `${label} complete` });

      if (teamId) {
        await loadTeamData(teamId, canPreviewLlm);
      }
      onSuccess?.();

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

  const jiraHref = (id: string) => {
    if (!selectedTeam?.jira_base_url) return null;
    return `${selectedTeam.jira_base_url.replace(/\/$/, "")}/browse/${id}`;
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
        <div className="header-banner">
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
          tone="blue"
          onClick={() => act("Sync Git", () => syncGit(teamId!), () => setActiveTab("dashboard"))}
        />
        <Button
          kind="secondary"
          label={busy === "Sync Jira" ? "Syncing…" : "Sync Jira now"}
          disabled={!teamId || !!busy}
          tone="blue"
          onClick={() => act("Sync Jira", () => syncJira(teamId!), () => setActiveTab("dashboard"))}
        />
        <Button
          kind="secondary"
          label={busy === "Snapshot metrics" ? "Snapshotting…" : "Snapshot metrics"}
          disabled={!teamId || !!busy}
          tone="teal"
          onClick={() => act("Snapshot metrics", () => snapshotMetrics(teamId!), () => setActiveTab("dashboard"))}
        />
        <Button
          label={busy === "Run weekly plan" ? "Planning…" : "Run weekly plan"}
          disabled={!teamId || !!busy}
          tone="green"
          onClick={() => act("Run weekly plan", () => runWeeklyPlan(teamId!), () => setActiveTab("plan"))}
        />
        {canPreviewLlm ? (
          <Button
            kind="secondary"
            label={busy === "Preview LLM data" ? "Loading…" : "Preview LLM data"}
            disabled={!teamId || !!busy}
            tone="violet"
            onClick={() =>
              act("Preview LLM data", async () => {
                const ctx = await getLlmContextPreview(teamId!);
                setLlmContext(JSON.stringify(ctx, null, 2));
                setShowLlmContext(true);
                return ctx;
              })
            }
          />
        ) : null}
      </div>

      <div className="tab-card-wrap">
        <div className="tab-bar">
          <button
            className={`tab-btn ${activeTab === "dashboard" ? "active" : ""}`}
            onClick={() => setActiveTab("dashboard")}
          >
            Dashboard
          </button>
          <button
            className={`tab-btn ${activeTab === "plan" ? "active" : ""}`}
            onClick={() => setActiveTab("plan")}
          >
            Weekly plan
          </button>
        </div>

      {activeTab === "dashboard" ? (
        <DashboardCard
          selectedTeamId={selectedTeam?.id ?? null}
          repoLabels={prs ? prs.map((repo) => `${repo.owner}/${repo.repo}`).join(", ") : ""}
          healthTone={healthTone}
          prTotal={prTotal}
          prSegments={prSegments}
          prTotalForMeter={prTotalForMeter}
          latestMetric={latestMetric}
          formatNumber={formatNumber}
          criticalPrs={criticalPrs}
      criticalIssues={criticalIssues}
      prHref={prHref}
      jiraHref={jiraHref}
      flagLabel={flagLabel}
      weekSeries={weekSeries}
          showMetricsHistory={showMetricsHistory}
          setShowMetricsHistory={setShowMetricsHistory}
          recentMetrics={recentMetrics}
          latestMetrics={latestMetrics}
        />
      ) : (
        <Card title="Weekly plan" right={plan ? <span className="muted small">Latest</span> : null}>
          {plan ? (
            <PlanView plan={plan} rawJson={rawJson} pull_requests={prs} showRawJson={canPreviewLlm} />
            ) : (
              <div className="muted">
                No plan yet. Click <code>Run weekly plan</code>.
              </div>
            )}
          </Card>
        )}


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
      </div>
    </div>
  );
}

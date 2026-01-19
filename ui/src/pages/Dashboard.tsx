import { useEffect, useMemo, useState } from "react";
import type { Team, WeeklyPlan, Metric, GitHubConfig } from "../types";
import { getTeams, getLatestPlan, runWeeklyPlan, snapshotMetrics, syncGithub, getLatestMetrics, getGithubConfig } from "../api";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { PlanView } from "../components/PlanView";
import { MetricsTable } from "../components/MetricsTable";


type Toast = { kind: "ok" | "error"; message: string } | null;

export default function Dashboard() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [teamId, setTeamId] = useState<number | null>(null);
  const [plan, setPlan] = useState<WeeklyPlan | null>(null);
  const [rawJson, setRawJson] = useState<string | null>(null);

  const [busy, setBusy] = useState<string | null>(null);
  const [toast, setToast] = useState<Toast>(null);
  const [metrics, setMetrics] = useState<Metric[]>([])
  const [gh, setGh] = useState<GitHubConfig | null>(null);

  const selectedTeam = useMemo(() => teams.find(t => t.id === teamId) ?? null, [teams, teamId]);

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
  (async () => {
    const p = await getLatestPlan(teamId);
    setPlan(p);
    setRawJson(p ? JSON.stringify(p, null, 2) : null);

    const ms = await getLatestMetrics(teamId);
    setMetrics(ms);

    const cfg = await getGithubConfig(teamId);
    setGh(cfg);
  })().catch((e: any) => {
    setToast({ kind: "error", message: e?.message ?? String(e) });
  });
}, [teamId]);

  const act = async (label: string, fn: () => Promise<any>) => {
    setBusy(label);
    setToast(null);
    try {
      await fn();
      setToast({ kind: "ok", message: `${label} complete` });

      if (teamId) {
        const p = await getLatestPlan(teamId);
        setPlan(p);
        setRawJson(p ? JSON.stringify(p, null, 2) : null);

        const ms = await getLatestMetrics(teamId);
        setMetrics(ms);

        const cfg = await getGithubConfig(teamId);
        setGh(cfg);
      }

    } catch (e: any) {
      setToast({ kind: "error", message: e?.message ?? String(e) });
    } finally {
      setBusy(null);
    }
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

      <div className="grid grid-2">
        <Card
          title="Controls"
          right={
            <span className="muted small">
              {selectedTeam ? `Team #${selectedTeam.id}` : ""}
              {gh?.owner && gh?.repo ? ` · ${gh.owner}/${gh.repo}` : ""}
            </span>
          }
        >
          <div className="row">
            <Button
              kind="secondary"
              label={busy === "Sync GitHub" ? "Syncing…" : "Sync GitHub now"}
              disabled={!teamId || !!busy}
              onClick={() => act("Sync GitHub", () => syncGithub(teamId!))}
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
          </div>

          <hr className="soft" />

          <div className="muted">
            Suggested demo flow: <code>Sync</code> → <code>Snapshot</code> → <code>Plan</code>
          </div>

          <div style={{ marginTop: 12 }}>
            <div style={{ fontWeight: 900, marginBottom: 8 }}>Latest snapshot metrics</div>
            <MetricsTable metrics={metrics} />
          </div>

        </Card>

        <Card title="Weekly plan" right={plan ? <span className="muted small">Latest</span> : null}>
          {plan ? (
            <PlanView plan={plan} rawJson={rawJson} ghcfg={gh} />
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

import type { WeeklyPlan, GitPullRequestMap } from "../types";
import { Badge } from "./Badge";

function getRepoConfig(prNum: number, pull_requests: GitPullRequestMap[] | null) {
  if (!pull_requests) return null;
  for (const repo of pull_requests) {
    if (repo.pull_requests.includes(prNum)) {
      return repo;
    }
  }
  return null;
}

function linkifyPRs(text: string, pull_requests: GitPullRequestMap[] | null) {
  // Matches: PR-123, pr-123, #123
  const re = /(PR-?\s*\d+|#\d+)/gi;

  const parts = text.split(re);
  return parts.map((part, i) => {
    const m = part.match(/(PR-?\s*(\d+)|#(\d+))/i);
    const prNum = m ? (m[2] ?? m[3]) : null;
    if (!prNum) return <span key={i}>{part}</span>;

    const repo = getRepoConfig(Number(prNum), pull_requests);
    const href = `${repo?.web_base_url.replace(/\/$/, "")}/${repo?.owner}/${repo?.repo}/pull/${prNum}`;
    const label = part.replace(/\s+/g, "");
    return (
      <a
        key={i}
        href={href}
        target="_blank"
        rel="noreferrer"
        style={{ textDecoration: "underline" }}
      >
        {label}
      </a>
    );
  });
}

const pct = (x: number) => `${Math.round((Number.isFinite(x) ? x : 0) * 100)}%`;

export function PlanView(props: { plan: WeeklyPlan; rawJson?: string | null; pull_requests: GitPullRequestMap[] | null }) {
  const p = props.plan;


  return (
    <div className="grid" style={{ gap: 12 }}>
      <div className="muted">
        Week start:{" "}
        <strong style={{ color: "rgba(255,255,255,0.92)" }}>
          {p.week_start}
        </strong>{" "}
        · Generated:{" "}
        <strong style={{ color: "rgba(255,255,255,0.92)" }}>
          {p.generated_at}
        </strong>
      </div>

      {p.summary ? (
        <div className="notice">
          <strong>Summary</strong>
          <div
            style={{
              marginTop: 6,
              color: "rgba(255,255,255,0.78)",
              lineHeight: 1.45,
            }}
          >
            {p.summary}
          </div>
        </div>
      ) : null}

      <div>
        <div style={{ fontWeight: 900, marginBottom: 8 }}>Top actions</div>
        <div className="grid" style={{ gap: 10 }}>
          {(p.top_actions || []).map((a, idx) => (
            <div key={idx} className="notice">
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 12,
                  flexWrap: "wrap",
                }}
              >
                <div style={{ fontWeight: 900 }}>
                  {idx + 1}. {a.title}
                </div>
                <div className="muted">
                  Confidence:{" "}
                  <strong style={{ color: "rgba(255,255,255,0.92)" }}>
                    {pct(a.confidence)}
                  </strong>
                </div>
              </div>

              <div
                style={{
                  marginTop: 8,
                  color: "rgba(255,255,255,0.78)",
                  lineHeight: 1.5,
                }}
              >
                <div>
                  <strong>Impact:</strong> {a.expected_impact}
                </div>
                <div style={{ marginTop: 6 }}>
                  <strong>Why:</strong> {a.rationale}
                </div>

                {a.evidence?.length ? (
                  <div style={{ marginTop: 6 }}>
                    <strong>Evidence:</strong>{" "}
                    <span className="muted">
                      {a.evidence.map((e, idx) => (
                        <span key={idx}>
                          {idx ? "; " : ""}
                          {linkifyPRs(e, props.pull_requests)}
                        </span>
                      ))}
                    </span>
                  </div>
                ) : null}

                {a.steps?.length ? (
                  <div style={{ marginTop: 8 }}>
                    <strong>Steps</strong>
                    <ol style={{ marginTop: 6, marginBottom: 0 }}>
                      {a.steps.slice(0, 3).map((s, i) => (
                        <li key={i} style={{ marginBottom: 6 }}>
                          {s}
                        </li>
                      ))}
                    </ol>
                  </div>
                ) : null}

                <div style={{ marginTop: 6 }}>
                  <strong>Risk:</strong> {a.risk}
                </div>
              </div>
            </div>
          ))}
          {!p.top_actions || p.top_actions.length === 0 ? (
            <div className="muted">No actions returned.</div>
          ) : null}
        </div>
      </div>

      <div>
        <div style={{ fontWeight: 900, marginBottom: 8 }}>Top risks</div>
        <div className="grid" style={{ gap: 10 }}>
          {(p.top_risks || []).map((r, idx) => (
            <div key={idx} className="notice" style={{ borderStyle: "dashed" }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 12,
                  flexWrap: "wrap",
                }}
              >
                <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                  <Badge kind={r.severity} text={r.severity.toUpperCase()} />
                  <div style={{ fontWeight: 900 }}>{r.title}</div>
                </div>
                <div className="muted">
                  Likelihood:{" "}
                  <strong style={{ color: "rgba(255,255,255,0.92)" }}>
                    {pct(r.likelihood)}
                  </strong>
                </div>
              </div>

              <div
                style={{
                  marginTop: 8,
                  color: "rgba(255,255,255,0.78)",
                  lineHeight: 1.45,
                }}
              >
                {r.description}
              </div>

              {r.mitigations?.length ? (
                <div
                  style={{
                    marginTop: 8,
                    color: "rgba(255,255,255,0.78)",
                    lineHeight: 1.45,
                  }}
                >
                  <strong>Mitigations:</strong>{" "}
                  <span className="muted">
                    {r.mitigations.slice(0, 3).join("; ")}
                  </span>
                </div>
              ) : null}
            </div>
          ))}
          {!p.top_risks || p.top_risks.length === 0 ? (
            <div className="muted">No risks returned.</div>
          ) : null}
        </div>
      </div>

      {props.rawJson ? (
        <details>
          <summary className="muted">Show raw JSON</summary>
          <pre
            style={{
              whiteSpace: "pre-wrap",
              marginTop: 10,
              padding: 12,
              borderRadius: 14,
              border: "1px solid rgba(255,255,255,0.08)",
              background: "rgba(0,0,0,0.25)",
            }}
          >
            {props.rawJson}
          </pre>
        </details>
      ) : null}
    </div>
  );
}

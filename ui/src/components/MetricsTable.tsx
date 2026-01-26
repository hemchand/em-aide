import type { Metric } from "../types";

const METRIC_LABELS: Record<string, string> = {
  pr_count: "PRs total",
  pr_open_count: "Open PRs",
  pr_avg_cycle_hours: "Avg cycle time (hours)",
  pr_avg_first_review_latency_hours: "Avg first review latency (hours)",
  pr_stale_count: "Stale PRs (>7 days)",
  pr_mega_count: "Mega PRs (>= 2000 changes)",
  pr_low_review_coverage_count: "PRs needing review",
  jira_blocked_rate: "Jira blocked rate",
  jira_wip_count: "Jira WIP count",
  jira_issue_count: "Jira issue count",
};

const labelFor = (name: string) => METRIC_LABELS[name] ?? name.replace(/_/g, " ");

export function MetricsTable(props: { metrics: Metric[] }) {
  if (!props.metrics.length) {
    return <div className="muted">No metrics yet. Click <code>Snapshot metrics</code>.</div>;
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Metric</th>
          <th>Value</th>
          <th>As of</th>
        </tr>
      </thead>
      <tbody>
        {props.metrics.map((m, i) => (
          <tr key={i}>
            <td>{labelFor(m.name)}</td>
            <td>{Number.isFinite(m.value) ? m.value.toFixed(3) : String(m.value)}</td>
            <td>{m.as_of_date}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

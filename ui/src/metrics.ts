export const METRIC_LABELS: Record<string, string> = {
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

export const metricLabel = (name: string) => METRIC_LABELS[name] ?? name.replace(/_/g, " ");

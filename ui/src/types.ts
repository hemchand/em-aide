export type Team = { id: number; name: string };

export type Action = {
  title: string;
  rationale: string;
  evidence: string[];
  steps: string[];
  expected_impact: string;
  risk: string;
  confidence: number;
};

export type Risk = {
  title: string;
  description: string;
  severity: "low" | "medium" | "high";
  likelihood: number;
  signals: string[];
  mitigations: string[];
};

export type WeeklyPlan = {
  week_start: string;
  generated_at: string;
  top_actions: Action[];
  top_risks: Risk[];
  summary: string;
};

export type Metric = {
  name: string;
  value: number;
  as_of_date: string;
};

export type GitPullRequestMap = {
  owner: string;
  repo: string;
  api_base_url?: string;
  web_base_url?: string;
  pull_requests: number[];
};

import type { Team, WeeklyPlan, Metric, GitPullRequestMap } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// These exist as /api aliases in the “one-command” backend zip
export const getTeams = () => request<Team[]>("/api/teams");
export const snapshotMetrics = (teamId: number) =>
  request(`/api/teams/${teamId}/metrics/snapshot`, { method: "POST" });
export const runWeeklyPlan = (teamId: number) =>
  request(`/api/teams/${teamId}/plan/run`, { method: "POST" });
export const getLatestPlan = async (teamId: number): Promise<WeeklyPlan | null> => {
  try {
    const data = await request<{ weekly_plan_id: number; plan: string }>(
      `/api/teams/${teamId}/plan/latest`
    );
    return JSON.parse(data.plan) as WeeklyPlan;
  } catch {
    return null;
  }
};

// Git sync endpoint might be non-/api in your backend (depends on whether you added the alias).
// This calls the non-/api path which should exist if you implemented manual sync earlier.
export const syncGit = (teamId: number) =>
  request(`/teams/${teamId}/sync/git`, { method: "POST" });

export const getLatestMetrics = async (teamId: number): Promise<Metric[]> => {
  // expects backend endpoint: GET /api/teams/{team_id}/metrics/latest
  return request<Metric[]>(`/api/teams/${teamId}/metrics/latest`);
};

export const getGitPullRequests = (teamId: number) =>
  request<GitPullRequestMap>(`/api/teams/${teamId}/git/pull/requests`);

export const getLlmContextPreview = (teamId: number) =>
  request<any>(`/api/teams/${teamId}/llm/context/preview`);

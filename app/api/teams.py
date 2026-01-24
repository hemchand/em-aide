from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import db_dep
from app import models  # adjust

router = APIRouter(tags=["teams"])

@router.get("/teams")
def list_teams(db: Session = Depends(db_dep)):
    teams = db.query(models.Team).all()
    return [{"id": t.id, "name": t.name} for t in teams]

@router.get("/teams/{team_id}/git/pull/requests")
def api_git_pull_requests(team_id: int, db: Session = Depends(db_dep)):
    get_web_url = lambda repo: repo.api_base_url.replace("api.", "").replace("/api/v3", "")
    repos = db.query(models.GitRepo).filter_by(team_id=team_id).all()
    repo_map = {repo.id: {"owner": repo.owner, "repo": repo.repo, "api_base_url": repo.api_base_url, "web_base_url": get_web_url(repo), "pull_requests": []} for repo in repos}
    prs = db.query(models.PullRequest).filter_by(team_id=team_id).all()
    for pr in prs:
        repo_info = repo_map.get(pr.git_repo_id)
        if repo_info:
            repo_info["pull_requests"].append(pr.pr_number)
    return list(repo_map.values())

@router.get("/teams/{team_id}/llm/runs")
def llm_runs(team_id: int, db: Session = Depends(db_dep)):
    runs = (db.query(models.AgentRun)
        .filter_by(team_id=team_id)
        .order_by(models.AgentRun.created_at.desc())
        .limit(50).all())
    return [
        {
            "id": r.id,
            "team_id": r.team_id,
            "created_at": r.created_at,
            "llm_mode": r.llm_mode,
            "model": r.model,
            "status": r.status,
            "error": r.error,
        }
        for r in runs
    ]

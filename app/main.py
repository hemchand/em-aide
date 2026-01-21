from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import json
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db import SessionLocal, init_db
from app import models
from app.services import ensure_defaults_setup, run_weekly_plan
from app.metrics.compute import snapshot_metrics
from app.ingest.git_ingest import sync_git
from app.logging import get_logger

log = get_logger("main")

app = FastAPI(title="EM-Aide")
templates = Jinja2Templates(directory="app/templates")

UI_DIST = "/app/ui-dist"
if os.path.isdir(UI_DIST):
    # Serve the React app at /app (single-origin, no CORS)
    app.mount("/app", StaticFiles(directory=UI_DIST, html=True), name="ui")

    @app.get("/app/{full_path:path}")
    def spa_fallback(full_path: str):
        index_path = os.path.join(UI_DIST, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"error": "UI not built"}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def _startup():
    init_db()
    # Create default org/team and configs from env
    db = SessionLocal()
    try:
        ensure_defaults_setup(db)
    finally:
        db.close()

@app.get("/health")
def health():
    return {"status": "ok", "project": "EM-Aide"}

@app.get("/api/health")
def api_health():
    return health()

@app.get("/api/teams")
def api_teams(db: Session = Depends(get_db)):
    teams = db.query(models.Team).all()
    return [{"id": t.id, "name": t.name} for t in teams]

@app.post("/api/teams/{team_id}/metrics/snapshot")
def api_snapshot_metrics_alias(team_id: int, db: Session = Depends(get_db)):
    return api_snapshot_metrics(team_id=team_id, db=db)

@app.post("/api/teams/{team_id}/plan/run")
def api_run_plan_alias(team_id: int, db: Session = Depends(get_db)):
    return api_run_plan(team_id=team_id, db=db)

@app.get("/api/teams/{team_id}/plan/latest")
def api_latest_plan_alias(team_id: int, db: Session = Depends(get_db)):
    return api_latest_plan(team_id=team_id, db=db)

@app.get("/api/teams/{team_id}/git/pull/requests")
def api_git_pull_requests(team_id: int, db: Session = Depends(get_db)):
    get_web_url = lambda repo: repo.api_base_url.replace("api.", "").replace("/api/v3", "")
    repos = db.query(models.GitRepo).filter_by(team_id=team_id).all()
    repo_map = {repo.id: {"owner": repo.owner, "repo": repo.repo, "api_base_url": repo.api_base_url, "web_base_url": get_web_url(repo), "pull_requests": []} for repo in repos}
    prs = db.query(models.PullRequest).filter_by(team_id=team_id).all()
    for pr in prs:
        repo_info = repo_map.get(pr.git_repo_id)
        if repo_info:
            repo_info["pull_requests"].append(pr.pr_number)
    return list(repo_map.values())

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    teams = db.query(models.Team).all()
    team = teams[0] if teams else None

    latest_plan = None
    latest_plan_obj = None
    if team:
        latest_plan_obj = (db.query(models.WeeklyPlan)
                           .filter_by(team_id=team.id)
                           .order_by(models.WeeklyPlan.created_at.desc())
                           .first())
        if latest_plan_obj:
            latest_plan = latest_plan_obj.plan_json

    # latest metrics
    metrics = []
    if team:
        snaps = (db.query(models.MetricSnapshot)
                 .filter_by(team_id=team.id)
                 .order_by(models.MetricSnapshot.as_of_date.desc())
                 .limit(20).all())
        if snaps:
            latest_date = snaps[0].as_of_date
            metrics = [s for s in snaps if s.as_of_date == latest_date]

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "team": team,
        "teams": teams,
        "latest_plan_json": latest_plan,
        "latest_plan_id": latest_plan_obj.id if latest_plan_obj else None,
        "metrics": metrics,
    })

@app.post("/teams/{team_id}/metrics/snapshot")
def api_snapshot_metrics(team_id: int, db: Session = Depends(get_db)):
    n = snapshot_metrics(team_id=team_id, db=db)
    return {"snapshots_written": n}

@app.post("/teams/{team_id}/plan/run")
def api_run_plan(team_id: int, db: Session = Depends(get_db)):
    wp = run_weekly_plan(db=db, team_id=team_id)
    return {"weekly_plan_id": wp.id, "week_start": str(wp.week_start)}

@app.get("/teams/{team_id}/plan/latest")
def api_latest_plan(team_id: int, db: Session = Depends(get_db)):
    wp = (db.query(models.WeeklyPlan)
          .filter_by(team_id=team_id)
          .order_by(models.WeeklyPlan.created_at.desc())
          .first())
    if not wp:
        return JSONResponse({"error": "no plan yet"}, status_code=404)
    return JSONResponse(content={"weekly_plan_id": wp.id, "plan": wp.plan_json})

@app.get("/runs", response_class=HTMLResponse)
def runs(request: Request, db: Session = Depends(get_db)):
    runs = (db.query(models.AgentRun)
            .order_by(models.AgentRun.created_at.desc())
            .limit(50).all())
    return templates.TemplateResponse("runs.html", {"request": request, "runs": runs})

@app.get("/api/teams/{team_id}/metrics/latest")
def api_latest_metrics(team_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(models.MetricSnapshot)
        .filter(models.MetricSnapshot.team_id == team_id)
        .order_by(models.MetricSnapshot.as_of_date.desc(), models.MetricSnapshot.id.desc())
        .limit(200)
        .all()
    )

    # return a compact list (name/value/date)
    return [{"name": r.name, "value": r.value, "as_of_date": str(r.as_of_date)} for r in rows]

#TODO: Remove after model changes
@app.post("/teams/{team_id}/sync/git")
def api_sync_git(team_id: int, db: Session = Depends(get_db)):
    team = db.query(models.Team).filter_by(id=team_id).one()
    pr_count = sync_git(team_id=team.id, db=db, since_days=30)

    return {
        "status": "ok",
        "prs_synced": pr_count
    }

@app.get("/api/teams/{team_id}/llm/context/preview")
def api_llm_context_preview(team_id: int, db: Session = Depends(get_db)):
    if os.getenv("ENVIRONMENT") not in ("local", "dev"):
        raise HTTPException(status_code=403, detail="Disabled in this environment")

    packet = db.query(models.ContextPacket).filter_by(team_id=team_id).order_by(models.ContextPacket.created_at.desc()).first()

    return json.loads(packet.content_json)

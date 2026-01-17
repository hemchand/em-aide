from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db import SessionLocal, init_db
from app.settings import settings
from app import models
from app.services import ensure_default_org_team, upsert_configs, run_weekly_plan
from app.metrics.compute import snapshot_metrics
from app.ingest.github_ingest import sync_github
from app.logging import get_logger

log = get_logger("api")

app = FastAPI(title="EM-Aide")
templates = Jinja2Templates(directory="app/templates")

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
        team = ensure_default_org_team(db, settings.default_org_name, settings.default_team_name)
        upsert_configs(
            db,
            team,
            github_cfg=dict(
                api_base_url=settings.github_api_base_url,
                token_present=bool(settings.github_token),
                owner=settings.github_owner,
                repo=settings.github_repo,
            ),
            jira_cfg=(dict(
                base_url=settings.jira_base_url,
                email=settings.jira_email,
                token_present=bool(settings.jira_api_token),
                project_key=settings.jira_project_key,
                board_id=settings.jira_board_id,
            ) if settings.jira_base_url and settings.jira_email and settings.jira_project_key else None)
        )
    finally:
        db.close()

@app.get("/health")
def health():
    return {"status": "ok", "project": "EM-Aide"}

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


@app.post("/teams/{team_id}/sync/github")
def api_sync_github(team_id: int, db: Session = Depends(get_db)):
    team = db.query(models.Team).filter_by(id=team_id).one()
    ghcfg = db.query(models.GitHubConfig).filter_by(team_id=team.id).one()

    pr_count = sync_github(
        team_id=team.id,
        api_base_url=ghcfg.api_base_url,
        token=settings.github_token,
        owner=ghcfg.owner,
        repo=ghcfg.repo,
        db=db,
        since_days=30,
    )
    return {"status": "ok", "prs_synced": pr_count, "repo": f"{ghcfg.owner}/{ghcfg.repo}"
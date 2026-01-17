import time
import datetime as dt
from apscheduler.schedulers.blocking import BlockingScheduler

from app.db import SessionLocal, init_db
from app.settings import settings
from app import models
from app.services import ensure_default_org_team, upsert_configs
from app.ingest.github_ingest import sync_github
from app.ingest.jira_ingest import sync_jira
from app.metrics.compute import snapshot_metrics
from app.logging import get_logger

log = get_logger("worker")


def _get_team(db):
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
        ) if settings.jira_base_url and settings.jira_email and settings.jira_project_key and settings.jira_api_token else None)
    )
    return team

def job_sync():
    db = SessionLocal()
    try:
        team = _get_team(db)
        ghcfg = db.query(models.GitHubConfig).filter_by(team_id=team.id).one()
        n = sync_github(
            team_id=team.id,
            api_base_url=ghcfg.api_base_url,
            token=settings.github_token,
            owner=ghcfg.owner,
            repo=ghcfg.repo,
            db=db,
            since_days=30
        )
        log.info(f"github synced: {n} PRs")

        if settings.jira_base_url and settings.jira_email and settings.jira_api_token and settings.jira_project_key:
            jcfg = db.query(models.JiraConfig).filter_by(team_id=team.id).one_or_none()
            if jcfg:
                m = sync_jira(
                    team_id=team.id,
                    base_url=jcfg.base_url,
                    email=jcfg.email,
                    api_token=settings.jira_api_token,
                    project_key=jcfg.project_key,
                    db=db,
                    max_results=200
                )
                log.info(f"jira synced: {m} issues")

    finally:
        db.close()

def job_metrics():
    db = SessionLocal()
    try:
        team = _get_team(db)
        n = snapshot_metrics(team_id=team.id, db=db, as_of=dt.date.today())
        log.info(f"metrics snapshotted: {n}")
    finally:
        db.close()

def main():
    init_db()
    sched = BlockingScheduler(timezone=settings.model_config.get("timezone", None) or "UTC")

    # Hourly sync
    sched.add_job(job_sync, "interval", minutes=settings.sync_interval_minutes, next_run_time=dt.datetime.utcnow())
    # Daily metrics (also run once on start)
    sched.add_job(job_metrics, "cron", hour=settings.metrics_daily_hour, minute=settings.metrics_daily_minute)
    sched.add_job(job_metrics, "date", run_date=dt.datetime.utcnow() + dt.timedelta(seconds=10))

    print("[worker] started. Press Ctrl+C to exit.")
    sched.start()

if __name__ == "__main__":
    main()

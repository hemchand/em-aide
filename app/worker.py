import time
import datetime as dt
from apscheduler.schedulers.blocking import BlockingScheduler
from app.db import SessionLocal, init_db
from app.settings import settings
from app import models
from app.services.setup import ensure_defaults_setup
from app.ingest.git_ingest import SyncInProgress, sync_team_git
from app.ingest.jira_ingest import sync_jira
from app.metrics.compute import snapshot_metrics
from app.logging import get_logger

log = get_logger("worker")


def _get_team(db):
    team =ensure_defaults_setup(db)
    return team

def _record_job_run(db, team_id: int, action: str, ran_at: dt.datetime | None = None) -> None:
    run = models.JobRun(team_id=team_id, action=action, ran_at=ran_at or dt.datetime.utcnow())
    db.add(run)
    db.commit()

def _get_last_job_run_time(db, team_id: int, action: str) -> dt.datetime | None:
    row = (db.query(models.JobRun)
        .filter_by(team_id=team_id, action=action)
        .order_by(models.JobRun.ran_at.desc())
        .first())
    return row.ran_at if row else None

def job_sync():
    db = SessionLocal()
    try:
        team = _get_team(db)
        try:
            n = sync_team_git(team_id=team.id, db=db, since_days=30, owner="worker")
            log.info(f"git sync completed")
            _record_job_run(db, team.id, "sync_git")
        except SyncInProgress:
            log.info("git sync skipped: already running")

        if settings.jira_base_url and settings.jira_email and settings.jira_api_token and settings.jira_project_key:
            try:
                m = sync_jira(team_id=team.id, db=db, owner="worker")
                log.info(f"jira synced: {m} issues")
            except SyncInProgress:
                log.info("jira sync skipped: already running")

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
    db = SessionLocal()
    try:
        team = _get_team(db)
        last_run = _get_last_job_run_time(db, team.id, "sync_git")
    finally:
        db.close()

    now = dt.datetime.utcnow()
    if not last_run:
        next_sync_run = now
    else:
        elapsed = now - last_run
        if elapsed > dt.timedelta(minutes=settings.sync_interval_minutes):
            next_sync_run = now
        else:
            next_sync_run = last_run + dt.timedelta(minutes=settings.sync_interval_minutes)

    sched.add_job(job_sync, "interval", minutes=settings.sync_interval_minutes, next_run_time=next_sync_run)
    # Daily metrics (also run once on start)
    sched.add_job(job_metrics, "cron", hour=settings.metrics_daily_hour, minute=settings.metrics_daily_minute)
    sched.add_job(job_metrics, "date", run_date=dt.datetime.utcnow() + dt.timedelta(seconds=10))

    print("[worker] started. Press Ctrl+C to exit.")
    sched.start()

if __name__ == "__main__":
    main()


import datetime as dt

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app import models
from app.ingest.github_ingest import sync_github
from app.settings import settings
from app.logging import get_logger

log = get_logger("git_ingest")

class SyncInProgress(Exception):
    pass

def _acquire_sync_lock(db: Session, team_id: int, *, action: str, owner: str | None, ttl_minutes: int = 120) -> None:
    now = dt.datetime.utcnow()
    lock = models.ActionLock(team_id=team_id, action=action, owner=owner, locked_at=now)
    try:
        db.add(lock)
        db.commit()
        return
    except IntegrityError:
        db.rollback()

    existing = db.query(models.ActionLock).filter_by(team_id=team_id, action=action).one_or_none()
    if existing and (now - existing.locked_at) > dt.timedelta(minutes=ttl_minutes):
        db.delete(existing)
        db.commit()
        try:
            db.add(lock)
            db.commit()
            return
        except IntegrityError:
            db.rollback()

    raise SyncInProgress(f"action already running for team {team_id}")

def _release_sync_lock(db: Session, team_id: int, *, action: str) -> None:
    db.query(models.ActionLock).filter_by(team_id=team_id, action=action).delete()
    db.commit()

def sync_team_git(team_id: int, db: Session, since_days: int = 30, owner: str | None = None) -> int:
    _acquire_sync_lock(db, team_id, action="sync_git", owner=owner)
    try:
        git_repos = db.query(models.GitRepo).filter_by(team_id=team_id).all()
        total = 0
        for repo in git_repos:
            if repo.git_provider.name.lower() == "github":
                n = sync_github(
                    team_id=team_id,
                    git_repo_id=repo.id,
                    api_base_url=repo.api_base_url,
                    token=settings.github_token,
                    owner=repo.owner,
                    repo=repo.repo,
                    db=db,
                    since_days=since_days
                )
                total += n
                log.info(f"github synced: {n} PRs for repo {repo.owner}/{repo.repo}")
        return total
    finally:
        _release_sync_lock(db, team_id, action="sync_git")

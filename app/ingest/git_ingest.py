
from sqlalchemy.orm import Session
from app import models
from app.ingest.github_ingest import sync_github
from app.settings import settings
from app.logging import get_logger

log = get_logger("git_ingest")

def sync_git(team_id: int, db: Session, since_days: int = 30) -> int:
    git_repos = db.query(models.GitRepo).filter_by(team_id=team_id).all()
    for ghcfg in git_repos:
        if ghcfg.git_provider.name.lower() == "github":
            n = sync_github(
                team_id=team_id,
                git_repo_id=ghcfg.id,
                api_base_url=ghcfg.api_base_url,
                token=settings.github_token,
                owner=ghcfg.owner,
                repo=ghcfg.repo,
                db=db,
                since_days=30
            )
            log.info(f"github synced: {n} PRs for repo {ghcfg.owner}/{ghcfg.repo}")
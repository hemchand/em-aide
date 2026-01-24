
from sqlalchemy.orm import Session
from app import models
from app.ingest.github_ingest import sync_github
from app.settings import settings
from app.logging import get_logger

log = get_logger("git_ingest")

def sync_team_git(team_id: int, db: Session, since_days: int = 30) -> int:
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
import datetime as dt
from sqlalchemy.orm import Session
from app.connectors.github_client import GitHubClient
from app import models
from app.util import sha256_64
from app.logging import get_logger

log = get_logger("github_ingest")

def _sync_pr_reviews(team_id: int, git_repo_id: int, pr_number: int, pr, db: Session) -> int:
    """Sync reviews for a single PR. Stores only hashed reviewer login + state + submitted_at."""
    from app.util import sha256_64
    from app import models as m
    count = 0
    try:
        reviews = pr.get_reviews()
    except Exception:
        return 0

    for rv in reviews:
        try:
            reviewer = rv.user.login if rv.user else "unknown"
            reviewer_hash = sha256_64(reviewer)
            submitted_at = rv.submitted_at.replace(tzinfo=None) if rv.submitted_at else None
            if not submitted_at:
                continue
            state = (rv.state or "COMMENTED")
            existing = (db.query(m.PullRequestReview)
                        .filter_by(team_id=team_id, git_repo_id=git_repo_id, pr_number=pr_number,
                                   reviewer_login_hash=reviewer_hash, submitted_at=submitted_at)
                        .one_or_none())
            if existing:
                existing.state = state
            else:
                db.add(m.PullRequestReview(
                    team_id=team_id,
                    git_repo_id=git_repo_id,
                    pr_number=pr_number,
                    reviewer_login_hash=reviewer_hash,
                    state=state,
                    submitted_at=submitted_at
                ))
            count += 1
        except Exception:
            continue
    return count

def sync_github(team_id: int, git_repo_id:int, api_base_url: str, token: str | None, owner: str, repo: str, db: Session, since_days: int = 30) -> int:
    client = GitHubClient(api_base_url=api_base_url, token=token)
    count = 0
    review_count = 0
    repo_obj = client.get_repo(owner, repo)
    full_name = repo_obj.full_name
    log.info(f"Syncing GitHub PRs for repo: {full_name}")

    for pr in client.iter_pull_requests(owner, repo, since_days=since_days):
        title_hash = sha256_64(pr.title or "")
        author_hash = sha256_64((pr.user.login if pr.user else "unknown"))
        additions = getattr(pr, "additions", None)
        deletions = getattr(pr, "deletions", None)
        changed_files = getattr(pr, "changed_files", None)

        existing = db.query(models.PullRequest).filter_by(team_id=team_id, git_repo_id=git_repo_id, pr_number=pr.number).one_or_none()
        if existing:
            existing.state = pr.state
            existing.merged_at = pr.merged_at.replace(tzinfo=None) if pr.merged_at else None
            existing.closed_at = pr.closed_at.replace(tzinfo=None) if pr.closed_at else None
            existing.additions = additions
            existing.deletions = deletions
            existing.changed_files = changed_files
            existing.updated_at = dt.datetime.utcnow()
        else:
            row = models.PullRequest(
                team_id=team_id,
                git_repo_id=git_repo_id,
                pr_number=pr.number,
                title_hash=title_hash,
                state=pr.state,
                created_at=pr.created_at.replace(tzinfo=None) if pr.created_at else dt.datetime.utcnow(),
                merged_at=pr.merged_at.replace(tzinfo=None) if pr.merged_at else None,
                closed_at=pr.closed_at.replace(tzinfo=None) if pr.closed_at else None,
                additions=additions,
                deletions=deletions,
                changed_files=changed_files,
                author_login_hash=author_hash,
            )
            db.add(row)
        review_count += _sync_pr_reviews(team_id, git_repo_id, pr.number, pr, db)
        count += 1

    db.commit()
    return count

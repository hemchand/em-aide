import datetime as dt
from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models

def compute_metrics(team_id: int, db: Session) -> dict[str, float]:
    # GitHub metrics from PR table + reviews table
    prs = db.query(models.PullRequest).filter_by(team_id=team_id).all()
    reviews = db.query(models.PullRequestReview).filter_by(team_id=team_id).all()

    # Index reviews by (repo_full_name, pr_number)
    rv_map: dict[tuple[str,int], list[models.PullRequestReview]] = {}
    for rv in reviews:
        rv_map.setdefault((rv.repo_full_name, rv.pr_number), []).append(rv)

    now = dt.datetime.utcnow()

    cycle_hours = []
    first_review_latency_hours = []
    open_pr_count = 0
    stale_prs = 0
    mega_prs = 0
    low_review_coverage = 0

    for pr in prs:
        is_open = pr.merged_at is None and pr.closed_at is None
        if is_open:
            open_pr_count += 1

        # cycle time
        if pr.merged_at:
            cycle_hours.append((pr.merged_at - pr.created_at).total_seconds() / 3600.0)

        # stale
        age_days = (now - pr.created_at).total_seconds() / 86400.0
        if is_open and age_days > 7:
            stale_prs += 1

        # size / mega
        size = (pr.additions or 0) + (pr.deletions or 0)
        if size >= 2000:
            mega_prs += 1

        # review latency + coverage
        pr_reviews = rv_map.get((pr.repo_full_name, pr.pr_number), [])
        if pr_reviews:
            first = min(pr_reviews, key=lambda r: r.submitted_at)
            first_review_latency_hours.append((first.submitted_at - pr.created_at).total_seconds()/3600.0)
        else:
            # Only count as low coverage for open PRs older than 24h
            if is_open and age_days > 1:
                low_review_coverage += 1

    avg_cycle = sum(cycle_hours)/len(cycle_hours) if cycle_hours else 0.0
    avg_first_review_latency = sum(first_review_latency_hours)/len(first_review_latency_hours) if first_review_latency_hours else 0.0

    # Jira lightweight metrics
    issues = db.query(models.Issue).filter_by(team_id=team_id).all()
    blocked = sum(1 for i in issues if i.is_blocked)
    in_progress = sum(1 for i in issues if i.status.lower() in {"in progress","doing","development","implementing"})
    total_issues = len(issues)

    blocked_rate = (blocked/total_issues) if total_issues else 0.0
    wip = float(in_progress)

    metrics = {
        "pr_count": float(len(prs)),
        "pr_open_count": float(open_pr_count),
        "pr_avg_cycle_hours": float(avg_cycle),
        "pr_avg_first_review_latency_hours": float(avg_first_review_latency),
        "pr_stale_count": float(stale_prs),
        "pr_mega_count": float(mega_prs),
        "pr_low_review_coverage_count": float(low_review_coverage),
        "jira_blocked_rate": float(blocked_rate),
        "jira_wip_count": float(wip),
        "jira_issue_count": float(total_issues),
    }
    return metrics


def snapshot_metrics(team_id: int, db: Session, as_of: dt.date | None = None) -> int:
    as_of = as_of or dt.date.today()
    metrics = compute_metrics(team_id, db)
    upserts = 0
    for name, value in metrics.items():
        existing = db.query(models.MetricSnapshot).filter_by(team_id=team_id, as_of_date=as_of, name=name).one_or_none()
        if existing:
            existing.value = float(value)
        else:
            db.add(models.MetricSnapshot(team_id=team_id, as_of_date=as_of, name=name, value=float(value)))
        upserts += 1
    db.commit()
    return upserts

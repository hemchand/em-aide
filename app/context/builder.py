import datetime as dt
from sqlalchemy.orm import Session
from app import models
from app.schemas import ContextPacketSchema, Signal, EntityRef
from app.util import sha256_short

def build_context_packet(team: models.Team, db: Session) -> ContextPacketSchema:
    # Pull latest metrics (today or most recent)
    snapshots = (db.query(models.MetricSnapshot)
                 .filter(models.MetricSnapshot.team_id == team.id)
                 .order_by(models.MetricSnapshot.as_of_date.desc())
                 .limit(50)
                 .all())
    # Use latest date among snapshots
    latest_date = snapshots[0].as_of_date if snapshots else dt.date.today()
    day_metrics = [s for s in snapshots if s.as_of_date == latest_date]

    signals = []
    for s in day_metrics:
        unit = "count"
        if "rate" in s.name or "avg" in s.name:
            unit = "ratio" if "rate" in s.name else "hours"
        signals.append(Signal(name=s.name, value=float(s.value), unit=unit))

    now = dt.datetime.utcnow()
    # Top PR entities: oldest open + mega PRs
    prs = (db.query(models.PullRequest)
           .filter_by(team_id=team.id)
           .order_by(models.PullRequest.created_at.asc())
           .limit(200)
           .all())
    entities: list[EntityRef] = []
    for pr in prs[:40]:
        age_days = (now - pr.created_at).total_seconds()/86400.0
        size = float((pr.additions or 0) + (pr.deletions or 0))
        flags = []
        if pr.merged_at is None and age_days > 7:
            flags.append("stale_pr")
        if size >= 2000:
            flags.append("mega_pr")
        entities.append(EntityRef(
            kind="pr",
            id=f"PR-{pr.pr_number}",
            state="merged" if pr.merged_at else pr.state,
            age_days=round(age_days, 2),
            size=size,
            flags=flags
        ))

    # Top Jira issues: oldest updated not available without history; use updated_at age proxy
    issues = (db.query(models.Issue)
              .filter_by(team_id=team.id)
              .limit(200)
              .all())
    for iss in issues[:40]:
        age_days = None
        if iss.updated_at:
            age_days = (now - iss.updated_at).total_seconds()/86400.0
        flags = []
        if iss.is_blocked:
            flags.append("blocked")
        entities.append(EntityRef(
            kind="issue",
            id=f"JIRA-{iss.key}",
            state=iss.status,
            age_days=round(age_days,2) if age_days is not None else None,
            size=None,
            flags=flags
        ))

    # Strict: no names or titles included.
    packet = ContextPacketSchema(
        org=team.org.name,
        team=team.name,
        as_of=now,
        goals=[
            "Improve delivery predictability this week",
            "Reduce PR review latency and avoid risky merges",
        ],
        signals=signals,
        entities=entities[:60],
        history={}
    )
    return packet

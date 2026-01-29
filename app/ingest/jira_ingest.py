import datetime as dt
from app import logging
from sqlalchemy.orm import Session
from app.settings import settings
from app.connectors.jira_client import JiraClient
from app.ingest.git_ingest import SyncInProgress, _acquire_sync_lock, _release_sync_lock
from app import models
from app.util import sha256_64

logger = logging.get_logger(__name__)

def _parse_jira_datetime(raw_value: object) -> dt.datetime | None:
    if not raw_value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(str(raw_value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        logger.warning("Failed to parse JIRA datetime %r: %s", raw_value, exc)
        return None
    if parsed.tzinfo is None:
        return parsed
    return parsed.astimezone(dt.timezone.utc).replace(tzinfo=None)

def sync_jira(team_id: int, db: Session, owner: str | None = None) -> int:
    _acquire_sync_lock(db, team_id, action="sync_jira", owner=owner)
    try:
        jcfg = db.query(models.JiraConfig).filter_by(team_id=team_id).one_or_none()
        if not jcfg:
            raise Exception("Jira config not found")
        if not settings.jira_api_token:
            raise Exception("JIRA_API_TOKEN not configured")
    
        client = JiraClient(base_url=jcfg.base_url, email=jcfg.email, api_token=settings.jira_api_token)
        issues = client.get_active_sprint_issues(project_key=jcfg.project_key, max_results=200)

        count = 0
        for issue in issues:
            fields = issue.fields
            status = getattr(fields.status, "name", "Unknown")
            issue_type = getattr(fields.issuetype, "name", "Unknown")
            priority = getattr(getattr(fields, "priority", None), "name", None)
            assignee = getattr(getattr(fields, "assignee", None), "displayName", None)
            assignee_hash = sha256_64(assignee) if assignee else None

            created_at = _parse_jira_datetime(getattr(fields, "created", None))
            updated_at = _parse_jira_datetime(getattr(fields, "updated", None))

            existing = db.query(models.Issue).filter_by(team_id=team_id, key=issue.key).one_or_none()
            if existing:
                existing.status = status
                existing.issue_type = issue_type
                existing.priority = priority
                existing.assignee_hash = assignee_hash
                if updated_at is not None:
                    existing.updated_at = updated_at
            else:
                row = models.Issue(
                    team_id=team_id,
                    key=issue.key,
                    status=status,
                    issue_type=issue_type,
                    priority=priority,
                    assignee_hash=assignee_hash,
                    created_at=created_at,
                    updated_at=updated_at,
                    due_date=getattr(fields, "duedate", None),
                )
                db.add(row)
            count += 1

        db.commit()
        return count
    finally:
        _release_sync_lock(db, team_id, action="sync_jira")

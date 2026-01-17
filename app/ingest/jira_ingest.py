import datetime as dt
from sqlalchemy.orm import Session
from app.connectors.jira_client import JiraClient
from app import models
from app.util import sha256_64

def sync_jira(team_id: int, base_url: str, email: str, api_token: str, project_key: str, db: Session, max_results: int = 200) -> int:
    client = JiraClient(base_url=base_url, email=email, api_token=api_token)
    issues = client.get_active_sprint_issues(project_key=project_key, max_results=max_results)

    count = 0
    for issue in issues:
        fields = issue.fields
        status = getattr(fields.status, "name", "Unknown")
        issue_type = getattr(fields.issuetype, "name", "Unknown")
        priority = getattr(getattr(fields, "priority", None), "name", None)
        assignee = getattr(getattr(fields, "assignee", None), "displayName", None)
        assignee_hash = sha256_64(assignee) if assignee else None

        created_at = None
        updated_at = None
        try:
            created_at = dt.datetime.fromisoformat(str(fields.created).replace("Z","+00:00")).replace(tzinfo=None)
        except Exception:
            pass
        try:
            updated_at = dt.datetime.fromisoformat(str(fields.updated).replace("Z","+00:00")).replace(tzinfo=None)
        except Exception:
            pass

        existing = db.query(models.Issue).filter_by(team_id=team_id, key=issue.key).one_or_none()
        if existing:
            existing.status = status
            existing.issue_type = issue_type
            existing.priority = priority
            existing.assignee_hash = assignee_hash
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
                is_blocked=False,
            )
            db.add(row)
        count += 1

    db.commit()
    return count

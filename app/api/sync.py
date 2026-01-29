from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import db_dep
from app import models
from app.settings import settings
from app.ingest.git_ingest import SyncInProgress, sync_team_git  # adjust
from app.ingest.jira_ingest import sync_jira

router = APIRouter(tags=["sync"])

@router.post("/teams/{team_id}/sync/git")
def sync_team_git_alias(team_id: int, db: Session = Depends(db_dep)):
    try:
        return sync_team_git(team_id=team_id, db=db, owner="api")
    except SyncInProgress as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

@router.post("/teams/{team_id}/sync/jira")
def sync_team_jira_alias(team_id: int, db: Session = Depends(db_dep)):
    try:
        m = sync_jira(team_id=team_id, db=db, owner="api")
        return {"issues_synced": m}
    except SyncInProgress as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

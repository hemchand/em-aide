from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import db_dep
from app.ingest.git_ingest import sync_team_git  # adjust

router = APIRouter(tags=["sync"])

@router.post("/teams/{team_id}/sync/git")
def sync_team_git_alias(team_id: int, db: Session = Depends(db_dep)):
    return sync_team_git(team_id=team_id, db=db)

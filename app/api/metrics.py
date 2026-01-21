from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app import models
from app.api.deps import db_dep
from app.metrics.compute import snapshot_metrics

router = APIRouter(tags=["metrics"])

@router.post("/teams/{team_id}/metrics/snapshot")
def snapshot(team_id: int, db: Session = Depends(db_dep)):
    return snapshot_metrics(team_id=team_id, db=db)

@router.get("/teams/{team_id}/metrics/latest")
def latest(team_id: int, db: Session = Depends(db_dep)):
    rows = (
        db.query(models.MetricSnapshot)
        .filter(models.MetricSnapshot.team_id == team_id)
        .order_by(models.MetricSnapshot.as_of_date.desc(), models.MetricSnapshot.id.desc())
        .limit(200)
        .all()
    )

    # return a compact list (name/value/date)
    return [{"name": r.name, "value": r.value, "as_of_date": str(r.as_of_date)} for r in rows]

import os
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app import models
from app.api.deps import db_dep
from app.services.plans import run_weekly_plan, get_latest_plan, get_llm_context_preview

router = APIRouter(tags=["plans"])

@router.post("/teams/{team_id}/plan/run")
def run(team_id: int, db: Session = Depends(db_dep)):
    wp = run_weekly_plan(db=db, team_id=team_id)
    return {"weekly_plan_id": wp.id, "week_start": str(wp.week_start)}

@router.get("/teams/{team_id}/plan/latest")
def latest(team_id: int, db: Session = Depends(db_dep)):
    wp = get_latest_plan(db, team_id)
    if not wp:
        return JSONResponse({"error": "no plan yet"}, status_code=404)
    return JSONResponse(content={"weekly_plan_id": wp.id, "plan": wp.plan_json})

@router.get("/teams/{team_id}/llm/context/preview")
def api_llm_context_preview(team_id: int, db: Session = Depends(db_dep)):
    if os.getenv("ENVIRONMENT") not in ("local", "dev"):
        raise HTTPException(status_code=403, detail="Disabled in this environment")

    packet = get_llm_context_preview(db, team_id)
    return json.loads(packet.content_json) if packet else {}
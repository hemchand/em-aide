
from sqlalchemy.orm import Session
from app import models
from app.settings import settings
from app.context.builder import build_context_packet
from app.agents.weekly_plan import generate_weekly_plan

def run_weekly_plan(db: Session, team_id: int) -> models.WeeklyPlan:
    team = db.query(models.Team).filter_by(id=team_id).one()
    # build and persist context packet
    packet = build_context_packet(team, db)
    cp = models.ContextPacket(team_id=team_id, content_json=packet.model_dump_json())
    db.add(cp)
    db.commit()
    db.refresh(cp)

    # create agent run record
    llm_mode = settings.llm_mode
    model = settings.llm_model if llm_mode == "remote" else settings.ollama_model
    ar = models.AgentRun(team_id=team_id, llm_mode=llm_mode, model=model, status="running")
    db.add(ar)
    db.commit()
    db.refresh(ar)

    try:
        plan = generate_weekly_plan(packet)
        ar.status = "ok"
        db.commit()
    except Exception as e:
        ar.status = "error"
        ar.error = str(e)
        db.commit()
        raise

    week_start = plan.week_start
    wp = models.WeeklyPlan(team_id=team_id, agent_run_id=ar.id, week_start=week_start, plan_json=plan.model_dump_json())
    db.add(wp)
    db.commit()
    db.refresh(wp)
    return wp

def get_latest_plan(db: Session, team_id: int) -> models.WeeklyPlan:
    return db.query(models.WeeklyPlan).filter_by(team_id=team_id)\
        .order_by(models.WeeklyPlan.created_at.desc()).first()

def get_llm_context_preview(db: Session, team_id: int) -> models.ContextPacket:
    return db.query(models.ContextPacket).filter_by(team_id=team_id)\
        .order_by(models.ContextPacket.created_at.desc()).first()

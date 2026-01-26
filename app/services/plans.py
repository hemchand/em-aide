
import datetime as dt

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app import models
from app.settings import settings
from app.context.builder import build_context_packet
from app.agents.weekly_plan import generate_weekly_plan

class PlanInProgress(Exception):
    pass

def _acquire_plan_lock(db: Session, team_id: int, *, owner: str | None, ttl_minutes: int = 60) -> None:
    now = dt.datetime.utcnow()
    lock = models.ActionLock(team_id=team_id, action="weekly_plan", owner=owner, locked_at=now)
    try:
        db.add(lock)
        db.commit()
        return
    except IntegrityError:
        db.rollback()

    existing = db.query(models.ActionLock).filter_by(team_id=team_id, action="weekly_plan").one_or_none()
    if existing and (now - existing.locked_at) > dt.timedelta(minutes=ttl_minutes):
        db.delete(existing)
        db.commit()
        try:
            db.add(lock)
            db.commit()
            return
        except IntegrityError:
            db.rollback()

    raise PlanInProgress(f"weekly plan already running for team {team_id}")

def _release_plan_lock(db: Session, team_id: int) -> None:
    db.query(models.ActionLock).filter_by(team_id=team_id, action="weekly_plan").delete()
    db.commit()

def run_weekly_plan(db: Session, team_id: int, owner: str | None = None) -> models.WeeklyPlan:
    _acquire_plan_lock(db, team_id, owner=owner)
    team = db.query(models.Team).filter_by(id=team_id).one()
    packet = build_context_packet(team, db)

    llm_mode = settings.llm_mode
    model = settings.llm_model if llm_mode == "remote" else settings.ollama_model

    try:
        plan = generate_weekly_plan(packet)
    except Exception as exc:
        with db.begin():
            cp = models.ContextPacket(team_id=team_id, content_json=packet.model_dump_json())
            db.add(cp)

            ar = models.AgentRun(
                team_id=team_id,
                llm_mode=llm_mode,
                model=model,
                status="error",
                error=str(exc),
            )
            db.add(ar)
        raise
    finally:
        _release_plan_lock(db, team_id)

    with db.begin():
        cp = models.ContextPacket(team_id=team_id, content_json=packet.model_dump_json())
        db.add(cp)

        ar = models.AgentRun(team_id=team_id, llm_mode=llm_mode, model=model, status="ok")
        db.add(ar)
        db.flush()

        wp = models.WeeklyPlan(
            team_id=team_id,
            agent_run_id=ar.id,
            week_start=plan.week_start,
            plan_json=plan.model_dump_json()
        )
        db.add(wp)

    db.refresh(wp)
    return wp

def get_latest_plan(db: Session, team_id: int) -> models.WeeklyPlan:
    return db.query(models.WeeklyPlan).filter_by(team_id=team_id)\
        .order_by(models.WeeklyPlan.created_at.desc()).first()

def get_llm_context_preview(db: Session, team_id: int) -> models.ContextPacket:
    return db.query(models.ContextPacket).filter_by(team_id=team_id)\
        .order_by(models.ContextPacket.created_at.desc()).first()

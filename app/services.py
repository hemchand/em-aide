import datetime as dt
from sqlalchemy.orm import Session
from app import models
from app.context.builder import build_context_packet
from app.agents.weekly_plan import generate_weekly_plan

def ensure_default_org_team(db: Session, org_name: str, team_name: str) -> models.Team:
    org = db.query(models.Org).filter_by(name=org_name).one_or_none()
    if not org:
        org = models.Org(name=org_name)
        db.add(org)
        db.commit()
        db.refresh(org)

    team = db.query(models.Team).filter_by(org_id=org.id, name=team_name).one_or_none()
    if not team:
        team = models.Team(org_id=org.id, name=team_name)
        db.add(team)
        db.commit()
        db.refresh(team)
    return team

def upsert_configs(db: Session, team: models.Team, github_cfg: dict, jira_cfg: dict | None):
    gh = db.query(models.GitHubConfig).filter_by(team_id=team.id).one_or_none()
    if not gh:
        gh = models.GitHubConfig(team_id=team.id, **github_cfg)
        db.add(gh)
    else:
        for k,v in github_cfg.items():
            setattr(gh, k, v)

    if jira_cfg:
        jc = db.query(models.JiraConfig).filter_by(team_id=team.id).one_or_none()
        if not jc:
            jc = models.JiraConfig(team_id=team.id, **jira_cfg)
            db.add(jc)
        else:
            for k,v in jira_cfg.items():
                setattr(jc, k, v)

    db.commit()

def run_weekly_plan(db: Session, team_id: int) -> models.WeeklyPlan:
    team = db.query(models.Team).filter_by(id=team_id).one()
    # build and persist context packet
    packet = build_context_packet(team, db)
    cp = models.ContextPacket(team_id=team_id, content_json=packet.model_dump_json())
    db.add(cp)
    db.commit()
    db.refresh(cp)

    # create agent run record
    from app.settings import settings
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

import datetime as dt
from sqlalchemy.orm import Session
from app import models
from app.settings import settings
from app.context.builder import build_context_packet
from app.agents.weekly_plan import generate_weekly_plan

def ensure_defaults_setup(db: Session) -> models.Team:
    team = ensure_default_org_team(db, settings.default_org_name, settings.default_team_name)
    github_provider = ensure_git_provider(db, "GitHub", "https://api.github.com")
    upsert_configs(
        db,
        team,
        git_cfg=dict(
            git_provider_id=github_provider.id,
            api_base_url=settings.github_api_base_url,
            token_present=bool(settings.github_token),
            owner=settings.github_owner,
            repo=settings.github_repo,
        ),
        jira_cfg=(dict(
            base_url=settings.jira_base_url,
            email=settings.jira_email,
            token_present=bool(settings.jira_api_token),
            project_key=settings.jira_project_key,
            board_id=settings.jira_board_id,
        ) if settings.jira_base_url and settings.jira_email and settings.jira_project_key and settings.jira_api_token else None)
    )
    return team

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

def ensure_git_provider(db: Session, name: str, api_base_url: str) -> models.GitProvider:
    gp = db.query(models.GitProvider).filter_by(name=name).one_or_none()
    if not gp:
        gp = models.GitProvider(name=name, api_base_url=api_base_url)
        db.add(gp)
        db.commit()
        db.refresh(gp)
    return gp

def upsert_configs(db: Session, team: models.Team, git_cfg: dict, jira_cfg: dict | None):
    repo = db.query(models.GitRepo).filter_by(team_id=team.id).one_or_none()
    if not repo:
        repo = models.GitRepo(team_id=team.id, **git_cfg)
        db.add(repo)
    else:
        for k,v in git_cfg.items():
            setattr(repo, k, v)

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

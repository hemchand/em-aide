import datetime as dt
from sqlalchemy import String, DateTime, Integer, Float, ForeignKey, Text, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base

class Org(Base):
    __tablename__ = "orgs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    teams: Mapped[list["Team"]] = relationship(back_populates="org")

class Team(Base):
    __tablename__ = "teams"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("orgs.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    org: Mapped["Org"] = relationship(back_populates="teams")
    git_repos: Mapped["GitRepo"] = relationship(back_populates="team", uselist=True)
    jira_config: Mapped["JiraConfig"] = relationship(back_populates="team", uselist=False)

class GitProvider(Base):
    __tablename__ = "git_providers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    api_base_url: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    git_repos: Mapped["GitRepo"] = relationship(back_populates="git_provider", uselist=True)

class GitRepo(Base):
    __tablename__ = "git_repos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    git_provider_id: Mapped[int] = mapped_column(ForeignKey("git_providers.id"))
    api_base_url: Mapped[str] = mapped_column(String(500))
    token_present: Mapped[bool] = mapped_column(Boolean, default=False)
    owner: Mapped[str] = mapped_column(String(200))
    repo: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    team: Mapped["Team"] = relationship(back_populates="git_repos")
    git_provider: Mapped["GitProvider"] = relationship(back_populates="git_repos")

    __table_args__ = (UniqueConstraint("team_id", "api_base_url", "owner", "repo", name="uq_repo"),)

class JiraConfig(Base):
    __tablename__ = "jira_configs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), unique=True)
    base_url: Mapped[str] = mapped_column(String(500))
    email: Mapped[str] = mapped_column(String(300))
    token_present: Mapped[bool] = mapped_column(Boolean, default=False)
    project_key: Mapped[str] = mapped_column(String(50))
    board_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    team: Mapped["Team"] = relationship(back_populates="jira_config")

class PullRequest(Base):
    __tablename__ = "pull_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    git_repo_id: Mapped[int] = mapped_column(ForeignKey("git_repos.id"), unique=False)
    pr_number: Mapped[int] = mapped_column(Integer, index=True)
    title_hash: Mapped[str] = mapped_column(String(64))  # store hash, not title
    state: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime)
    merged_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    additions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deletions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    changed_files: Mapped[int | None] = mapped_column(Integer, nullable=True)
    author_login_hash: Mapped[str] = mapped_column(String(64))
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    __table_args__ = (UniqueConstraint("team_id", "git_repo_id", "pr_number", name="uq_pr"),)

class Issue(Base):
    __tablename__ = "jira_issues"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    key: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[str] = mapped_column(String(100))
    issue_type: Mapped[str] = mapped_column(String(100))
    priority: Mapped[str | None] = mapped_column(String(100), nullable=True)
    assignee_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    due_date: Mapped[str | None] = mapped_column(String(30), nullable=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (UniqueConstraint("team_id", "key", name="uq_issue"),)

class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    as_of_date: Mapped[dt.date] = mapped_column()
    name: Mapped[str] = mapped_column(String(200), index=True)
    value: Mapped[float] = mapped_column(Float)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    __table_args__ = (UniqueConstraint("team_id", "as_of_date", "name", name="uq_metric"),)

class ContextPacket(Base):
    __tablename__ = "context_packets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    content_json: Mapped[str] = mapped_column(Text)  # store sanitized JSON

class AgentRun(Base):
    __tablename__ = "agent_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    llm_mode: Mapped[str] = mapped_column(String(20))
    model: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(50), default="ok")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

class PullRequestReview(Base):
    __tablename__ = "pull_request_reviews"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    git_repo_id: Mapped[int] = mapped_column(ForeignKey("git_repos.id"), unique=False)
    pr_number: Mapped[int] = mapped_column(Integer, index=True)
    reviewer_login_hash: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(50))  # APPROVED / CHANGES_REQUESTED / COMMENTED / DISMISSED
    submitted_at: Mapped[dt.datetime] = mapped_column(DateTime)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("team_id", "git_repo_id", "pr_number", "reviewer_login_hash", "submitted_at", name="uq_pr_review"),
    )

class WeeklyPlan(Base):
    __tablename__ = "weekly_plans"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    agent_run_id: Mapped[int] = mapped_column(ForeignKey("agent_runs.id"))
    week_start: Mapped[dt.date] = mapped_column()
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    plan_json: Mapped[str] = mapped_column(Text)

class ActionLock(Base):
    __tablename__ = "action_locks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    action: Mapped[str] = mapped_column(String(50))
    owner: Mapped[str | None] = mapped_column(String(50), nullable=True)
    locked_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    __table_args__ = (UniqueConstraint("team_id", "action", name="uq_action_lock"),)

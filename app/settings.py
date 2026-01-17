from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_port: int = Field(default=8080, alias="APP_PORT")
    database_url: str = Field(alias="DATABASE_URL")

    default_org_name: str = Field(default="demo-org", alias="DEFAULT_ORG_NAME")
    default_team_name: str = Field(default="demo-team", alias="DEFAULT_TEAM_NAME")

    github_api_base_url: str = Field(default="https://api.github.com", alias="GITHUB_API_BASE_URL")
    github_token: str | None = Field(default=None, alias="GITHUB_TOKEN")
    github_owner: str = Field(default="kubernetes", alias="GITHUB_OWNER")
    github_repo: str = Field(default="kubernetes", alias="GITHUB_REPO")

    jira_base_url: str | None = Field(default=None, alias="JIRA_BASE_URL")
    jira_email: str | None = Field(default=None, alias="JIRA_EMAIL")
    jira_api_token: str | None = Field(default=None, alias="JIRA_API_TOKEN")
    jira_project_key: str | None = Field(default=None, alias="JIRA_PROJECT_KEY")
    jira_board_id: str | None = Field(default=None, alias="JIRA_BOARD_ID")

    llm_mode: str = Field(default="remote", alias="LLM_MODE")  # remote | local
    llm_base_url: str = Field(default="https://api.openai.com/v1", alias="LLM_BASE_URL")
    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")
    llm_model: str = Field(default="gpt-4.1-mini", alias="LLM_MODEL")
    llm_temperature: float = Field(default=0.2, alias="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=1200, alias="LLM_MAX_TOKENS")
    llm_timeout_seconds: int = Field(default=60, alias="LLM_TIMEOUT_SECONDS")

    ollama_base_url: str = Field(default="http://host.docker.internal:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3.1", alias="OLLAMA_MODEL")

    sync_interval_minutes: int = Field(default=60, alias="SYNC_INTERVAL_MINUTES")
    metrics_daily_hour: int = Field(default=2, alias="METRICS_DAILY_HOUR")
    metrics_daily_minute: int = Field(default=0, alias="METRICS_DAILY_MINUTE")

settings = Settings()

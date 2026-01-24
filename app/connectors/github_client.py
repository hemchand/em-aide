import datetime as dt
from typing import Iterable, Optional
from github import Github
from github.Repository import Repository
from github.PullRequest import PullRequest as GhPR
from app.logging import get_logger

log = get_logger("github_client")

class GitHubClient:
    def __init__(self, api_base_url: str, token: Optional[str]):
        # PyGithub supports base_url via Github(base_url=...) but it expects the API root.
        # GitHub Cloud: https://api.github.com
        # GHE: https://<host>/api/v3
        kwargs = {}
        if api_base_url:
            kwargs["base_url"] = api_base_url
        self.gh = Github(login_or_token=token) if not kwargs else Github(login_or_token=token, **kwargs)

    def get_repo(self, owner: str, repo: str) -> Repository:
        return self.gh.get_repo(f"{owner}/{repo}")

    def iter_pull_requests(self, owner: str, repo: str, since_days: int = 30) -> Iterable[GhPR]:
        r = self.get_repo(owner, repo)
        since = dt.datetime.utcnow() - dt.timedelta(days=since_days)
        # Fetch closed PRs recently updated for better sample size
        pulls = r.get_pulls(state="all", sort="updated", direction="desc")
        for pr in pulls:
            try:
                log.info(f"Iterating PR #{pr.number} updated at {pr.updated_at}")
                if pr.updated_at and pr.updated_at.replace(tzinfo=None) < since:
                    break
                yield pr
            except Exception as exc:
                log.warning("Failed to iterate PR: %s", exc)
                continue

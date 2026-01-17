from __future__ import annotations
from typing import Optional, Iterable
from jira import JIRA
from app.settings import settings

class JiraClient:
    def __init__(self, base_url: str, email: str, api_token: str):
        self.jira = JIRA(server=base_url, basic_auth=(email, api_token))

    def search_issues(self, jql: str, max_results: int = 200):
        return self.jira.search_issues(jql, maxResults=max_results)

    def get_board(self, board_id: str):
        # Jira Agile API; available via jira client
        return self.jira.board(board_id)

    def get_active_sprint_issues(self, project_key: str, max_results: int = 200):
        # Simple JQL: issues in project updated recently
        jql = f'project = "{project_key}" ORDER BY updated DESC'
        return self.search_issues(jql, max_results=max_results)

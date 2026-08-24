"""数据适配器：把 app.pl_data.repository 适配为 ai_service 的 PlDataProvider 契约。

依赖方向：app ──► ai_service（接口由 AI 层定义，app 层实现并注入）。
AI 层因此对数据库、schema、SQL 完全无感知。
"""
from app.pl_data import repository


class RepositoryDataProvider:
    """仓储实现的数据提供者（无状态，可按请求创建）。"""

    def get_recent_form(self, team: str, n: int = 5):
        return repository.get_recent_form(team, n)

    def get_head_to_head(self, team_a: str, team_b: str, n: int = 5):
        return repository.get_head_to_head(team_a, team_b, n)

    def get_team_stats(self, team: str):
        return repository.get_team_stats(team)

    def get_standings(self):
        return repository.get_standings()

    def get_odds_history(self, match_uid: str):
        return repository.get_odds_history(match_uid)

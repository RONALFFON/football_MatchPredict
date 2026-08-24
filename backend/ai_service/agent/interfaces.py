"""英超数据提供者接口（依赖倒置的契约）。

设计意图：AI 能力层定义「需要什么数据」，app 层负责「怎么拿数据」。
ai_service 因此不 import 任何 app / scripts 模块，可独立测试与复用。

app 层的实现见：app/pl_data/provider.py（RepositoryDataProvider）。
"""
from typing import Dict, List, Protocol, runtime_checkable


@runtime_checkable
class PlDataProvider(Protocol):
    """英超数据查询契约（所有方法在数据缺失时应抛 ValueError）。"""

    def get_recent_form(self, team: str, n: int = 5) -> List[Dict]:
        """球队最近 n 场已完成比赛。"""
        ...

    def get_head_to_head(self, team_a: str, team_b: str, n: int = 5) -> List[Dict]:
        """两队最近 n 次交锋。"""
        ...

    def get_team_stats(self, team: str) -> Dict:
        """球队主客场进失球、胜平等聚合统计。"""
        ...

    def get_standings(self) -> List[Dict]:
        """当前积分榜（按名次升序）。"""
        ...

    def get_odds_history(self, match_uid: str) -> List[Dict]:
        """某场比赛的赔率时间序列。"""
        ...

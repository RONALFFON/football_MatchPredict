"""Agent 工具注册表：Gemini function 声明 + 本地执行。

架构约束：
1. 数据访问全部经由注入的 PlDataProvider，本模块零 SQL、零仓储依赖。
2. 任何工具异常都转为结构化错误，保证 ReAct 循环不中断。
"""
import math
from typing import Any, Dict, List

from ai_service.agent.interfaces import PlDataProvider

# ---------- Gemini function 声明（静态） ----------

TOOL_DECLARATIONS: List[Dict[str, Any]] = [
    {
        'name': 'query_recent_form',
        'description': '查询英超球队最近 N 场已完成比赛的比分与结果',
        'parameters': {
            'type': 'OBJECT',
            'properties': {
                'team': {'type': 'STRING', 'description': '球队名称，如 Arsenal'},
                'n': {'type': 'INTEGER', 'description': '场次，默认5'},
            },
            'required': ['team'],
        },
    },
    {
        'name': 'query_head_to_head',
        'description': '查询两支英超球队的历史交锋记录',
        'parameters': {
            'type': 'OBJECT',
            'properties': {
                'team_a': {'type': 'STRING'},
                'team_b': {'type': 'STRING'},
                'n': {'type': 'INTEGER', 'description': '场次，默认5'},
            },
            'required': ['team_a', 'team_b'],
        },
    },
    {
        'name': 'query_team_stats',
        'description': '查询英超球队的主客场进失球、胜平场次等聚合统计',
        'parameters': {
            'type': 'OBJECT',
            'properties': {'team': {'type': 'STRING'}},
            'required': ['team'],
        },
    },
    {
        'name': 'query_standings',
        'description': '查询英超当前积分榜',
        'parameters': {'type': 'OBJECT', 'properties': {}},
    },
    {
        'name': 'query_odds_movement',
        'description': '查询某场英超比赛（需 match_uid）的赔率时间序列',
        'parameters': {
            'type': 'OBJECT',
            'properties': {'match_uid': {'type': 'STRING'}},
            'required': ['match_uid'],
        },
    },
    {
        'name': 'predict_match',
        'description': '用泊松模型预测两支英超球队的胜平负概率与最可能比分',
        'parameters': {
            'type': 'OBJECT',
            'properties': {
                'home_team': {'type': 'STRING'},
                'away_team': {'type': 'STRING'},
            },
            'required': ['home_team', 'away_team'],
        },
    },
]


# ---------- 注册表（数据经 provider 注入） ----------

class ToolRegistry:
    """工具执行入口：编排器持有本实例，不直接接触 provider。"""

    def __init__(self, provider: PlDataProvider):
        self.provider = provider

    @property
    def declarations(self) -> List[Dict[str, Any]]:
        return TOOL_DECLARATIONS

    def execute(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return {'result': self._dispatch(name, args)}
        except ValueError as e:
            return {'error': str(e)}
        except Exception as e:  # pragma: no cover
            return {'error': f'工具执行失败: {e}'}

    def _dispatch(self, name: str, args: Dict[str, Any]) -> Any:
        p = self.provider
        if name == 'query_recent_form':
            return p.get_recent_form(args['team'], int(args.get('n', 5)))
        if name == 'query_head_to_head':
            return p.get_head_to_head(args['team_a'], args['team_b'], int(args.get('n', 5)))
        if name == 'query_team_stats':
            return p.get_team_stats(args['team'])
        if name == 'query_standings':
            return p.get_standings()
        if name == 'query_odds_movement':
            return p.get_odds_history(args['match_uid'])
        if name == 'predict_match':
            return self._predict_match(args['home_team'], args['away_team'])
        raise ValueError(f'未知工具: {name}')

    def _predict_match(self, home_team: str, away_team: str) -> Dict[str, Any]:
        """泊松比分矩阵 → 胜平负概率（主站 parlay_predictor 的建模思路）。"""
        home_stats = self.provider.get_team_stats(home_team)
        away_stats = self.provider.get_team_stats(away_team)

        home_xg = ((home_stats.get('home_goals_scored') or 1.3) * 0.7 +
                   (away_stats.get('away_goals_conceded') or 1.3) * 0.3) * 1.1
        away_xg = ((away_stats.get('away_goals_scored') or 1.1) * 0.7 +
                   (home_stats.get('home_goals_conceded') or 1.1) * 0.3) * 0.9

        def poisson(k: int, lam: float) -> float:
            return math.exp(-lam) * lam ** k / math.factorial(k)

        max_goals = 5
        score_probs: Dict[tuple, float] = {}
        home_win = draw = away_win = 0.0
        for i in range(max_goals + 1):
            for j in range(max_goals + 1):
                prob = poisson(i, home_xg) * poisson(j, away_xg)
                score_probs[(i, j)] = prob
                if i > j:
                    home_win += prob
                elif i == j:
                    draw += prob
                else:
                    away_win += prob
        top_scores = sorted(score_probs.items(), key=lambda x: x[1], reverse=True)[:3]
        return {
            'home_team': home_team,
            'away_team': away_team,
            'home_expected_goals': round(home_xg, 2),
            'away_expected_goals': round(away_xg, 2),
            'probabilities': {
                'home_win': round(home_win, 3),
                'draw': round(draw, 3),
                'away_win': round(away_win, 3),
            },
            'top_scores': [f'{i}-{j} ({p:.1%})' for (i, j), p in top_scores],
        }

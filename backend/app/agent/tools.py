"""Agent 工具注册表：每个工具 = Gemini function 声明 + 本地执行函数。

架构约束：工具实现只允许经由 app.pl_data.repository 访问数据，禁止散落裸 SQL。
"""
import math
from typing import Callable

from app.pl_data import repository

# ---------- Gemini function 声明 ----------

TOOL_DECLARATIONS = [
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

# ---------- 本地执行实现 ----------


def _predict_match(home_team: str, away_team: str) -> dict:
    """泊松比分矩阵 → 胜平负概率（复用主站 parlay_predictor 的建模思路）。"""
    home_stats = repository.get_team_stats(home_team)
    away_stats = repository.get_team_stats(away_team)

    home_xg = ((home_stats['home_goals_scored'] or 1.3) * 0.7 +
               (away_stats['away_goals_conceded'] or 1.3) * 0.3) * 1.1
    away_xg = ((away_stats['away_goals_scored'] or 1.1) * 0.7 +
               (home_stats['home_goals_conceded'] or 1.1) * 0.3) * 0.9

    def poisson(k: int, lam: float) -> float:
        return math.exp(-lam) * lam ** k / math.factorial(k)

    max_goals = 5
    score_probs: dict[tuple[int, int], float] = {}
    home_win = draw = away_win = 0.0
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            p = poisson(i, home_xg) * poisson(j, away_xg)
            score_probs[(i, j)] = p
            if i > j:
                home_win += p
            elif i == j:
                draw += p
            else:
                away_win += p
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


IMPLEMENTATIONS: dict[str, Callable[..., dict | list]] = {
    'query_recent_form': lambda **kw: repository.get_recent_form(kw['team'], int(kw.get('n', 5))),
    'query_head_to_head': lambda **kw: repository.get_head_to_head(kw['team_a'], kw['team_b'], int(kw.get('n', 5))),
    'query_team_stats': lambda **kw: repository.get_team_stats(kw['team']),
    'query_standings': lambda **kw: repository.get_standings(),
    'query_odds_movement': lambda **kw: repository.get_odds_history(kw['match_uid']),
    'predict_match': _predict_match,
}


def execute_tool(name: str, args: dict) -> dict:
    """执行工具；任何异常都转为结构化错误，保证 ReAct 循环不中断。"""
    impl = IMPLEMENTATIONS.get(name)
    if impl is None:
        return {'error': f'未知工具: {name}'}
    try:
        return {'result': impl(**args)}
    except ValueError as e:
        return {'error': str(e)}
    except Exception as e:  # pragma: no cover
        return {'error': f'工具执行失败: {e}'}

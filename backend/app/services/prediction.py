"""通用预测服务。"""
import math


def parse_odds(match: dict) -> tuple[float, float, float]:
    odds = match.get('odds') or {}
    if not isinstance(odds, dict):
        raise ValueError('赔率格式错误')
    if odds.get('type') == 'hhad' or str(odds.get('goal_line') or '0') not in {'0', '0.0', '+0', '-0'}:
        raise ValueError('当前仅支持普通胜平负赔率，请刷新获取非让球赔率')
    hhad = odds.get('hhad') or {}
    if not isinstance(hhad, dict):
        raise ValueError('赔率格式错误')
    values = (
        match.get('home_odds') if match.get('home_odds') is not None else hhad.get('h'),
        match.get('draw_odds') if match.get('draw_odds') is not None else hhad.get('d'),
        match.get('away_odds') if match.get('away_odds') is not None else hhad.get('a'),
    )
    if any(value is None for value in values):
        raise ValueError('缺少完整赔率，请刷新比赛数据')
    try:
        values = tuple(float(value) for value in values)
    except (TypeError, ValueError) as exc:
        raise ValueError('赔率格式错误') from exc
    if any(not math.isfinite(value) for value in values):
        raise ValueError('赔率必须为有限数值')
    if any(value <= 0 for value in values):
        raise ValueError('赔率必须大于0')
    return values


def simple_predict(matches: list[dict]) -> list[dict]:
    results = []
    for match in matches:
        home_odds, draw_odds, away_odds = parse_odds(match)
        inverse = {'home': 1 / home_odds, 'draw': 1 / draw_odds, 'away': 1 / away_odds}
        total = sum(inverse.values())
        probabilities = {key: round(value / total, 3) for key, value in inverse.items()}
        recommendation = max(probabilities, key=probabilities.get)
        results.append({
            'home_team': match.get('home_team', ''),
            'away_team': match.get('away_team', ''),
            'probabilities': probabilities,
            'odds': {'home': home_odds, 'draw': draw_odds, 'away': away_odds},
            'recommendation': {
                'home': '主胜', 'draw': '平局', 'away': '客胜'
            }[recommendation],
        })
    return results

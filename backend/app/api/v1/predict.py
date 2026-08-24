"""预测相关：简化赔率预测 + 保存预测结果（含权限校验）。"""
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.core.deps import get_db, get_current_user
from app.core.response import fail, ok

router = APIRouter(prefix='/api/v1', tags=['五大联赛-预测'])


class PredictRequest(BaseModel):
    mode: str = ''
    match_data: dict = {}
    prediction_result: str = ''
    confidence: float = 0
    ai_analysis: Optional[str] = None


@router.post('/predict')
def simple_predict(payload: dict):
    """基于赔率倒数归一化的兜底预测（无需登录）。"""
    matches = payload.get('matches', [])
    if not matches:
        return fail('未提供比赛数据')
    results = []
    for match in matches:
        try:
            home_odds = float(match.get('home_odds', 2.0))
            draw_odds = float(match.get('draw_odds', 3.0))
            away_odds = float(match.get('away_odds', 2.5))
        except (TypeError, ValueError):
            return fail('赔率格式错误')
        probs = {'home': 1 / home_odds, 'draw': 1 / draw_odds, 'away': 1 / away_odds}
        total = sum(probs.values())
        probs = {k: round(v / total, 3) for k, v in probs.items()}
        results.append({
            'home_team': match.get('home_team', ''),
            'away_team': match.get('away_team', ''),
            'probabilities': probs,
            'odds': {'home': home_odds, 'draw': draw_odds, 'away': away_odds},
            'recommendation': '主胜' if probs['home'] >= max(probs['draw'], probs['away'])
                              else ('平局' if probs['draw'] >= probs['away'] else '客胜'),
        })
    return ok({'individual_predictions': results}, '简化预测模式，推荐使用AI智能预测获得更准确结果')


@router.post('/save-prediction')
def save_prediction(payload: PredictRequest, request: Request,
                    user=Depends(get_current_user), db=Depends(get_db)):
    """保存预测结果：需登录且未超出每日配额。"""
    if db is None:
        return fail('数据库未配置', code=500)
    if user is None:
        return fail('请先登录再进行预测', code=401)
    if not db.can_user_predict(user['id'], user['user_type'], user['daily_predictions_used']):
        return fail('今日免费预测次数已用完，请升级会员', code=403)

    mode = payload.mode.lower()
    kwargs = dict(
        match_data=payload.match_data,
        prediction_result=payload.prediction_result,
        confidence=payload.confidence,
        user_ip=request.client.host if request.client else '',
        user_id=user['id'],
        username=user['username'],
    )
    savers = {'ai': db.save_ai_prediction, 'classic': db.save_classic_prediction,
              'lottery': db.save_lottery_prediction}
    if mode not in savers:
        return fail('未知的预测模式')
    if mode in ('ai', 'lottery'):
        kwargs['ai_analysis'] = payload.ai_analysis or ''

    try:
        if not savers[mode](**kwargs):
            return fail('预测结果保存失败', code=500)
        db.increment_user_predictions(user['id'])
        updated = db.get_user_by_username(user['username'])
        if not updated:
            return fail('预测成功，但获取用户状态失败', code=500)
        return ok({'user': _user_payload(updated)}, '预测结果保存成功')
    except Exception as e:  # pragma: no cover
        return fail(f'服务器错误: {e}', code=500)


@router.get('/prediction-stats')
def prediction_stats(db=Depends(get_db)):
    if db is None:
        return fail('数据库未配置', code=500)
    try:
        return ok(db.get_prediction_stats())
    except Exception as e:  # pragma: no cover
        return fail(f'获取统计信息失败: {e}', code=500)


def _user_payload(user: dict) -> dict:
    expires = user.get('membership_expires')
    return {
        'username': user['username'],
        'user_type': user['user_type'],
        'daily_predictions_used': user['daily_predictions_used'],
        'total_predictions': user['total_predictions'],
        'membership_expires': expires.isoformat() if expires else None,
    }

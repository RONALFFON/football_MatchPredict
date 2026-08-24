"""AI 智能预测：服务端代理 Gemini，密钥绝不暴露给前端。"""
import logging

from fastapi import APIRouter

from app.core.config import settings
from app.core.response import fail, ok

router = APIRouter(prefix='/api/v1/ai', tags=['五大联赛-AI预测'])
logger = logging.getLogger(__name__)

_predictor = None


def _get_predictor():
    """惰性初始化 AI 预测器（复用 scripts/ai_predictor.py）。"""
    global _predictor
    if _predictor is not None:
        return _predictor
    if not settings.gemini_api_key:
        return None
    try:
        from scripts.ai_predictor import AIFootballPredictor
        _predictor = AIFootballPredictor(api_key=settings.gemini_api_key,
                                         model_name=settings.gemini_model)
        return _predictor
    except Exception as e:  # pragma: no cover
        logger.error(f'AI预测器初始化失败: {e}')
        return None


@router.post('/predict')
def ai_predict(payload: dict):
    matches = payload.get('matches', [])
    if not matches:
        return fail('没有提供比赛数据')

    predictor = _get_predictor()
    if predictor is None:
        return fail('AI服务未配置（缺少 GEMINI_API_KEY）', code=500)

    try:
        analyses = predictor.analyze_matches(matches)
        results = [{
            'match_id': a.match_id,
            'home_team': a.home_team,
            'away_team': a.away_team,
            'league_name': a.league_name,
            'ai_analysis': a.ai_analysis,
            'odds': {'home': a.home_odds, 'draw': a.draw_odds, 'away': a.away_odds},
        } for a in analyses]
        return ok({'predictions': results, 'count': len(results)})
    except Exception as e:  # pragma: no cover
        logger.error(f'AI预测失败: {e}')
        return fail(f'AI预测失败: {e}', code=500)

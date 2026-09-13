"""AI 智能预测：服务端代理模型服务，密钥绝不暴露给前端。

实现已抽离至独立 AI 能力层 ai_service（本路由只做参数校验与结果透出）。
"""
import logging

from fastapi import APIRouter, Depends

from app.core.config import settings
from app.core.deps import get_current_user, get_users
from app.infrastructure.repositories import UserRepository, prediction_record
from app.core.security import create_token
from app.services.prediction import parse_odds
from app.core.response import fail, ok
from app.schemas.predict import MatchBatchRequest

router = APIRouter(prefix='/api/v1/ai', tags=['五大联赛-AI预测'])
logger = logging.getLogger(__name__)

_predictor = None


def _get_predictor():
    """惰性初始化 AI 预测器（来自 ai_service 能力层）。"""
    global _predictor
    if _predictor is not None:
        return _predictor
    try:
        from ai_service import FootballAiPredictor, OpenAICompatibleClient
        llm = OpenAICompatibleClient(
            settings.ai_api_key,
            settings.ai_model,
            settings.ai_client_base_url,
            mode=settings.ai_mode,
        )
        if not llm.available:
            return None
        _predictor = FootballAiPredictor(llm)
        return _predictor
    except Exception as e:  # pragma: no cover
        logger.error(f'AI预测器初始化失败: {e}')
        return None


@router.post('/predict')
def ai_predict(payload: MatchBatchRequest, user=Depends(get_current_user),
               users: UserRepository = Depends(get_users)):
    if user is None:
        return fail('请先登录再使用 AI 分析', code=401)
    predictor = _get_predictor()
    if predictor is None:
        return fail('AI服务未配置（请检查 AI_MODE、AI_BASE_URL 和 AI_API_KEY）', code=500)
    matches = [match.model_dump(exclude_none=True) for match in payload.matches]
    try:
        for match in matches:
            match['home_odds'], match['draw_odds'], match['away_odds'] = parse_odds(match)
    except ValueError as exc:
        return fail(str(exc))

    reserved = users.consume_prediction(user['id'], len(matches))
    if reserved is None:
        return fail('今日剩余次数不足，请减少比赛数量或升级会员', code=403)
    failed = len(matches)
    try:
        results = predictor.analyze_matches(matches)
        successful = sum(item.get('status') == 'success' for item in results)
        failed = len(matches) - successful
        for match, item in zip(matches, results):
            if item.get('status') == 'success':
                record = prediction_record(mode='ai', match_data=match, prediction_result='AI分析',
                                           confidence=None, user=user, user_ip='',
                                           ai_analysis=item.get('ai_analysis', ''))
                item['save_receipt'] = create_token({'purpose': 'prediction_save',
                                                     'user_id': user['id'], 'record': record})
        return ok({'predictions': results, 'count': len(results),
                   'success_count': successful, 'failed_count': failed})
    except Exception:
        failed = len(matches)
        logger.exception('AI预测失败')
        return fail('AI预测失败，请稍后重试', code=500)
    finally:
        if failed:
            users.release_prediction(user['id'], reserved['last_prediction_date'], failed)

"""AI 智能预测：服务端代理 Gemini，密钥绝不暴露给前端。

实现已抽离至独立 AI 能力层 ai_service（本路由只做参数校验与结果透出）。
"""
import logging

from fastapi import APIRouter

from app.core.config import settings
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
    if not settings.gemini_api_key:
        return None
    try:
        from ai_service import FootballAiPredictor, GeminiClient
        llm = GeminiClient(settings.gemini_api_key, settings.gemini_model)
        _predictor = FootballAiPredictor(llm)
        return _predictor
    except Exception as e:  # pragma: no cover
        logger.error(f'AI预测器初始化失败: {e}')
        return None


@router.post('/predict')
def ai_predict(payload: MatchBatchRequest):
    predictor = _get_predictor()
    if predictor is None:
        return fail('AI服务未配置（缺少 GEMINI_API_KEY）', code=500)

    try:
        matches = [match.model_dump(exclude_none=True) for match in payload.matches]
        results = predictor.analyze_matches(matches)  # ai_service 已返回结构化 dict 列表
        return ok({'predictions': results, 'count': len(results)})
    except Exception as e:  # pragma: no cover
        logger.error(f'AI预测失败: {e}')
        return fail(f'AI预测失败: {e}', code=500)

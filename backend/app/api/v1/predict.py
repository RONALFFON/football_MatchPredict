"""基础预测和预测记录 API。"""
from fastapi import APIRouter, Depends, Request

from app.core.deps import get_current_user, get_db, get_predictions
from app.core.response import fail, ok
from app.infrastructure.repositories import PredictionRepository, prediction_record
from app.schemas.predict import MatchBatchRequest, SavePredictionRequest
from app.services.auth import user_payload
from app.services.prediction import simple_predict


router = APIRouter(prefix='/api/v1', tags=['五大联赛-预测'])


@router.post('/predict')
def predict(payload: MatchBatchRequest):
    try:
        matches = [match.model_dump(exclude_none=True) for match in payload.matches]
        return ok({'individual_predictions': simple_predict(matches)}, '简化预测模式')
    except ValueError as exc:
        return fail(str(exc))


@router.post('/save-prediction')
def save_prediction(
    payload: SavePredictionRequest,
    request: Request,
    db=Depends(get_db),
    user=Depends(get_current_user),
    predictions: PredictionRepository = Depends(get_predictions),
):
    if not db.configured:
        return fail('数据库未配置', code=500)
    if user is None:
        return fail('请先登录再进行预测', code=401)
    mode = payload.mode.lower()
    if mode not in {'ai', 'classic', 'lottery'}:
        return fail('未知的预测模式')
    data = prediction_record(
        mode=mode,
        match_data=payload.match_data,
        prediction_result=payload.prediction_result,
        confidence=payload.confidence,
        ai_analysis=payload.ai_analysis or '',
        user=user,
        user_ip=request.client.host if request.client else '',
    )
    try:
        updated = predictions.save_with_quota(data)
        return ok({'user': user_payload(updated)}, '预测结果保存成功')
    except PermissionError as exc:
        return fail(str(exc), code=403)
    except Exception as exc:
        return fail(f'预测结果保存失败: {exc}', code=500)


@router.get('/prediction-stats')
def prediction_stats(
    db=Depends(get_db), predictions: PredictionRepository = Depends(get_predictions)
):
    if not db.configured:
        return fail('数据库未配置', code=500)
    try:
        return ok(predictions.stats())
    except Exception as exc:
        return fail(f'获取统计信息失败: {exc}', code=500)

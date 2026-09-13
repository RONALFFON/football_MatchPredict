"""基础预测和预测记录 API。"""
import json
from uuid import NAMESPACE_URL, uuid5

from fastapi import APIRouter, Depends, Request

from app.core.security import decode_token
from app.services.membership import business_now

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
    try:
        if mode == 'ai':
            receipt = decode_token(payload.save_receipt or '')
            if not receipt or receipt.get('purpose') != 'prediction_save' or receipt.get('user_id') != user['id']:
                return fail('请使用本账号 AI 分析返回的有效保存凭证', code=403)
            data = receipt.get('record')
            if not isinstance(data, dict) or data.get('user_id') != user['id']:
                return fail('保存凭证无效', code=403)
            data['user_ip'] = request.client.host if request.client else ''
        else:
            # 经典和彩票结果由服务端重算，不采信客户端提交的结果和置信度。
            match = dict(payload.match_data)
            for outcome in ('home', 'draw', 'away'):
                if match.get(f'{outcome}_odds') is None and outcome in match:
                    match[f'{outcome}_odds'] = match[outcome]
            if not all(isinstance(match.get(key), str) and 0 < len(match[key].strip()) <= 100
                       for key in ('home_team', 'away_team')):
                return fail('请填写有效主客队名称')
            result = simple_predict([match])[0]
            data = prediction_record(
                mode=mode, match_data=match, prediction_result=result['recommendation'],
                confidence=round(max(result['probabilities'].values()) * 10, 2),
                user=user, user_ip=request.client.host if request.client else '',
            )
            # 新客户端按单次分析生成请求编号；旧客户端同日同内容保存也去重。
            key = str(payload.request_id) if payload.request_id else json.dumps(
                [business_now().date().isoformat(), mode, match], ensure_ascii=False, sort_keys=True)
            data['prediction_id'] = f'{mode}_{uuid5(NAMESPACE_URL, str(user["id"]) + ":" + key).hex}'
        predictions.save(data)
        return ok({'user': user_payload(user), 'prediction_id': data['prediction_id']}, '预测结果保存成功')
    except ValueError as exc:
        return fail(str(exc))
    except Exception:
        return fail('预测结果保存失败，请稍后重试', code=500)


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

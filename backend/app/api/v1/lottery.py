"""体彩比赛数据 API。"""
from fastapi import APIRouter, Depends, Query

from app.core.deps import get_db, get_lottery, get_lottery_provider
from app.core.response import fail, ok
from app.infrastructure.providers.lottery import LotteryProvider
from app.infrastructure.repositories import LotteryRepository


router = APIRouter(prefix='/api/v1/lottery', tags=['五大联赛-彩票模式'])


@router.get('/matches')
def get_lottery_matches(
    days: int = Query(default=3, ge=1, le=7),
    db=Depends(get_db),
    lottery: LotteryRepository = Depends(get_lottery),
):
    if not db.configured:
        return fail('数据库未配置', code=500)
    try:
        matches = lottery.get_matches(days)
        if not matches:
            return fail('暂无比赛数据，请运行：cd backend && python -m app.workers.sync_lottery --days 7', code=404)
        return ok({'matches': matches, 'count': len(matches), 'source': 'database'}, f'从数据库获取 {len(matches)} 场比赛')
    except Exception as exc:
        return fail(f'数据库查询失败: {exc}', code=500)


@router.post('/refresh')
def refresh_lottery_data(
    days: int = Query(default=3, ge=1, le=7),
    provider: LotteryProvider = Depends(get_lottery_provider),
):
    try:
        matches = provider.get_matches(days_ahead=days)
        return ok({'matches': matches, 'count': len(matches)}, '刷新成功')
    except Exception as exc:
        return fail(f'刷新数据失败: {exc}', code=500)

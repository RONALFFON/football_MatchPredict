"""体彩比赛数据：数据库优先模式（数据由 scripts/sync_daily_matches.py 定时入库）。"""
from fastapi import APIRouter, Depends, Query

from app.core.deps import get_db
from app.core.response import fail, ok

router = APIRouter(prefix='/api/v1/lottery', tags=['五大联赛-彩票模式'])


@router.get('/matches')
def get_lottery_matches(days: int = Query(default=3, ge=1, le=7), db=Depends(get_db)):
    """获取体彩比赛数据（仅从数据库读取）。"""
    if db is None:
        return fail('数据库未配置', code=500)
    try:
        matches = db.get_daily_matches(days_ahead=days)
        if not matches:
            return fail('暂无比赛数据，请运行同步脚本：python scripts/sync_daily_matches.py --days 7', code=404)
        return ok({'matches': matches, 'count': len(matches), 'source': 'database'},
                  f'从数据库获取 {len(matches)} 场比赛')
    except Exception as e:  # pragma: no cover
        return fail(f'数据库查询失败: {e}', code=500)


@router.post('/refresh')
def refresh_lottery_data(days: int = Query(default=3, ge=1, le=7)):
    """实时从体彩官方 API 拉取（不入库，仅刷新展示）。"""
    try:
        from scripts.china_lottery_spider import ChinaLotterySpider
        matches = ChinaLotterySpider().get_formatted_matches(days_ahead=days)
        return ok({'matches': matches, 'count': len(matches)}, '刷新成功')
    except Exception as e:  # pragma: no cover
        return fail(f'刷新数据失败: {e}', code=500)

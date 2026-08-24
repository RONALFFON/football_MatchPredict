"""英超专项数据 API。"""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.response import fail, ok
from app.pl_data import repository

router = APIRouter(prefix='/api/v1/pl', tags=['英超专项-数据'])


@router.get('/matches')
def pl_matches(status: str | None = Query(default=None, description='SCHEDULED/LIVE/FINISHED'),
               limit: int = Query(default=50, ge=1, le=200)):
    try:
        return ok({'matches': repository.get_matches(status, limit)})
    except ValueError as e:
        return fail(str(e), code=404)


@router.get('/standings')
def pl_standings():
    try:
        return ok({'standings': repository.get_standings()})
    except ValueError as e:
        return fail(str(e), code=404)


@router.get('/teams/{name}')
def pl_team(name: str):
    """球队画像：基础信息 + 聚合统计 + 近5场。"""
    try:
        stats = repository.get_team_stats(name)
        recent = repository.get_recent_form(name, 5)
        return ok({'team': name, 'stats': stats, 'recent_form': recent})
    except ValueError as e:
        return fail(str(e), code=404)


@router.get('/odds/{match_uid}')
def pl_odds(match_uid: str):
    try:
        return ok({'history': repository.get_odds_history(match_uid)})
    except ValueError as e:
        return fail(str(e), code=404)

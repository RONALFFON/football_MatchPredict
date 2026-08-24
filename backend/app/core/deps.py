"""FastAPI 依赖注入。"""
from typing import Optional

from fastapi import Depends, Header

from app.core.security import decode_token
from app.infrastructure.database import database
from app.infrastructure.providers.lottery import LotteryProvider
from app.infrastructure.repositories import LotteryRepository, PredictionRepository, UserRepository


users = UserRepository(database)
predictions = PredictionRepository(database)
lottery = LotteryRepository(database)
lottery_provider = LotteryProvider()


def get_db():
    return database


def get_users() -> UserRepository:
    return users


def get_predictions() -> PredictionRepository:
    return predictions


def get_lottery() -> LotteryRepository:
    return lottery


def get_lottery_provider() -> LotteryProvider:
    return lottery_provider


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    user_repo: UserRepository = Depends(get_users),
) -> Optional[dict]:
    if not authorization or not authorization.lower().startswith('bearer '):
        return None
    payload = decode_token(authorization[7:].strip())
    if not payload or not database.configured:
        return None
    return user_repo.find_by_username(payload.get('username', ''))


def require_user(user=Depends(get_current_user)):
    if user is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail='请先登录')
    return user

"""MatchPredict v3 API。"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import agent_pl, ai, auth, lottery, pl_data, predict, teams  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.response import ok  # noqa: E402
from app.infrastructure.database import database  # noqa: E402

app = FastAPI(title='MatchPredict API', version='3.0.0', description='足球赛事分析 API')

origins = [item.strip() for item in settings.cors_origins.split(',') if item.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/health')
def health():
    return 'OK'


@app.get('/api/v1/meta')
def meta():
    """前端启动自检：服务状态与能力开关（不泄露任何密钥）。"""
    return ok({
        'db_ready': database.configured,
        'ai_ready': bool(settings.ai_api_key),
        'ai_model': settings.ai_model,
    })


app.include_router(teams.router)
app.include_router(lottery.router)
app.include_router(predict.router)
app.include_router(ai.router)
app.include_router(auth.router)
app.include_router(pl_data.router)
app.include_router(agent_pl.router)

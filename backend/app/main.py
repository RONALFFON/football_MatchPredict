"""MatchPredict 统一后端（FastAPI）

- /api/v1/*        五大联赛：球队/体彩赛程/预测/AI/认证
- /api/v1/pl/*     英超专项：数据查询 + AI Agent 对话
前端为 frontend/ 下的 Vue3 SPA，纯 JSON 交互，前后端分离。
"""
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 本地开发时加载 backend/.env（生产由平台注入环境变量）
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from app.api.v1 import agent_pl, ai, auth, lottery, pl_data, predict, teams  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.response import ok  # noqa: E402

app = FastAPI(title='MatchPredict API', version='2.0.0', description='五大联赛 + 英超专项分析统一后端')

origins = settings.cors_origins.split(',') if settings.cors_origins != '*' else ['*']
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,  # JWT 走 Authorization 头，无需 cookie 凭证
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/health')
def health():
    return 'OK'


@app.get('/api/v1/meta')
def meta():
    """前端启动自检：服务状态与能力开关（不泄露任何密钥）。"""
    from app.core.deps import prediction_db
    return ok({
        'db_ready': prediction_db is not None,
        'ai_ready': bool(settings.gemini_api_key),
        'ai_model': settings.gemini_model,
    })


app.include_router(teams.router)
app.include_router(lottery.router)
app.include_router(predict.router)
app.include_router(ai.router)
app.include_router(auth.router)
app.include_router(pl_data.router)
app.include_router(agent_pl.router)

"""英超 Agent 对话 API：SSE 流式。

AI 实现已抽离至独立能力层 ai_service；本路由负责：
登录/配额校验 → 组装 LLM 客户端与数据适配器 → 转发事件流。
"""
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ai_service import OpenAICompatibleClient, run_agent
from app.core.config import settings
from app.core.deps import get_current_user, get_users
from app.core.response import fail
from app.infrastructure.repositories import UserRepository
from app.pl_data.provider import RepositoryDataProvider

router = APIRouter(prefix='/api/v1/pl/agent', tags=['英超专项-AI Agent'])


class ChatMessage(BaseModel):
    role: str  # user / assistant
    text: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = Field(default_factory=list)


@router.post('/chat')
def pl_agent_chat(payload: ChatRequest,
                  user=Depends(get_current_user), users: UserRepository = Depends(get_users)):
    """Agent 对话：需登录；免费用户消耗每日配额（与五大联赛预测共用配额池）。"""
    if user is None:
        return fail('请先登录再使用 AI 分析', code=401)
    if not users.can_predict(user):
        return fail('今日免费次数已用完，请升级会员', code=403)

    history = [{'role': m.role, 'text': m.text} for m in payload.history]
    llm = OpenAICompatibleClient(
        settings.ai_api_key,
        settings.ai_model,
        settings.ai_client_base_url,
        mode=settings.ai_mode,
    )
    provider = RepositoryDataProvider()

    def event_stream():
        answered = False
        for event in run_agent(payload.message, history, llm=llm, provider=provider):
            if event['type'] == 'text_delta':
                answered = True
            yield f'data: {json.dumps(event, ensure_ascii=False)}\n\n'
        # 有有效回答才扣配额
        if answered:
            users.consume_prediction(user['id'])
        yield 'data: [DONE]\n\n'

    return StreamingResponse(event_stream(), media_type='text/event-stream',
                             headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

"""英超 Agent 对话 API：SSE 流式。

AI 实现已抽离至独立能力层 ai_service；本路由负责：
登录/配额校验 → 组装 LLM 客户端与数据适配器 → 转发事件流。
"""
import json
from typing import Literal

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
    role: Literal['user', 'assistant']
    text: str = Field(min_length=1, max_length=12000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)


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
    if not llm.available:
        return fail('AI服务未配置', code=503)
    provider = RepositoryDataProvider()

    def event_stream():
        reserved = users.consume_prediction(user['id'])
        if reserved is None:
            yield 'data: ' + json.dumps({'type': 'error', 'message': '今日免费次数已用完'}, ensure_ascii=False) + '\n\n'
            yield 'data: [DONE]\n\n'
            return
        answered = False
        try:
            for event in run_agent(payload.message, history, llm=llm, provider=provider):
                if event['type'] == 'text_delta' and event.get('text'):
                    answered = True
                yield f'data: {json.dumps(event, ensure_ascii=False)}\n\n'
        finally:
            # 已输出有效内容计一次；失败或提前断开且尚未输出内容则释放。
            if not answered:
                users.release_prediction(user['id'], reserved['last_prediction_date'])
        yield 'data: [DONE]\n\n'

    return StreamingResponse(event_stream(), media_type='text/event-stream',
                             headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

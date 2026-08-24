"""英超 Agent 对话 API：SSE 流式。"""
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agent.orchestrator import run_agent
from app.core.deps import get_current_user, get_db
from app.core.response import fail

router = APIRouter(prefix='/api/v1/pl/agent', tags=['英超专项-AI Agent'])


class ChatMessage(BaseModel):
    role: str  # user / assistant
    text: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


@router.post('/chat')
def pl_agent_chat(payload: ChatRequest,
                  user=Depends(get_current_user), db=Depends(get_db)):
    """Agent 对话：需登录；免费用户消耗每日配额（与五大联赛预测共用配额池）。"""
    if user is None:
        return fail('请先登录再使用 AI 分析', code=401)
    if db is not None and not db.can_user_predict(user['id'], user['user_type'],
                                                  user['daily_predictions_used']):
        return fail('今日免费次数已用完，请升级会员', code=403)

    history = [{'role': m.role, 'text': m.text} for m in payload.history]

    def event_stream():
        answered = False
        for event in run_agent(payload.message, history):
            if event['type'] == 'text_delta':
                answered = True
            yield f'data: {json.dumps(event, ensure_ascii=False)}\n\n'
        # 有有效回答才扣配额
        if answered and db is not None:
            db.increment_user_predictions(user['id'])
        yield 'data: [DONE]\n\n'

    return StreamingResponse(event_stream(), media_type='text/event-stream',
                             headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

"""AI 能力层（独立包，与 Web 应用层解耦）。

依赖方向（严格单向）：
    app（路由/仓储）──依赖──► ai_service
    ai_service ──零依赖──► app / scripts

对外仅暴露三个门面：
- OpenAICompatibleClient  通用 OpenAI 兼容 LLM 客户端（一般无需直接使用）
- FootballAiPredictor 五大联赛 AI 深度分析
- run_agent           英超 AI Agent 对话（ReAct + 工具）
"""
from ai_service.llm import OpenAICompatibleClient, extract_text
from ai_service.predictor import FootballAiPredictor
from ai_service.agent import run_agent

__all__ = ['OpenAICompatibleClient', 'extract_text', 'FootballAiPredictor', 'run_agent']

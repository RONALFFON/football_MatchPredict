"""预测接口数据模型。"""
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class MatchInput(BaseModel):
    match_id: Optional[str] = None
    home_team: str = Field(min_length=1, max_length=100)
    away_team: str = Field(min_length=1, max_length=100)
    league_name: str = ''
    home_odds: Optional[float] = None
    draw_odds: Optional[float] = None
    away_odds: Optional[float] = None
    odds: Dict[str, Any] = Field(default_factory=dict)


class MatchBatchRequest(BaseModel):
    matches: list[MatchInput] = Field(min_length=1)


class SavePredictionRequest(BaseModel):
    mode: str = ''
    match_data: Dict[str, Any] = Field(default_factory=dict)
    prediction_result: str = ''
    confidence: float = 0
    ai_analysis: Optional[str] = None

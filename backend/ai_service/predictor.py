"""五大联赛 AI 比赛预测：Prompt 构建 + 限流重试。

取代遗留 scripts/ai_predictor.py（其实现迁入本 AI 能力层，解除对旧脚本的依赖）。
app 层仅需使用 FootballAiPredictor，不接触任何 Gemini 协议细节。
"""
import logging
import random
import time
import uuid
from typing import Any, Dict, List, Optional

import requests

from ai_service.llm import GeminiClient, extract_text

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT_TEMPLATE = """请详细分析这场足球比赛并给出完整预测：

比赛：{home_team} vs {away_team}
联赛：{league_name}
赔率：主胜 {home_odds} | 平局 {draw_odds} | 客胜 {away_odds}

请按以下格式提供详细预测：

**一、比赛分析**
（考虑两队实力、近期状态、历史对战、主客场优势等因素）

**二、胜平负预测**
推荐结果：[主胜/平局/客胜]
推荐理由：
信心指数：[1-10]

**三、比分预测**
最可能比分：
其他可能比分：

**四、半场胜平负预测**
半场结果：[主胜/平局/客胜]
全场结果：[主胜/平局/客胜]
半全场组合：

**五、进球数预测**
总进球数：[0-1球/2-3球/4球以上]
主队进球：
客队进球：

**六、其他分析**
- 大小球分析
- 亚盘分析
- 风险提示

请用中文回答，保持专业分析水准。"""


class FootballAiPredictor:
    """五大联赛单场深度分析（一问一答模式，无工具调用）。"""

    MAX_RETRIES = 3

    def __init__(self, llm: GeminiClient):
        self.llm = llm

    def analyze_matches(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for match in matches:
            try:
                item = self._analyze_single(match)
                if item:
                    results.append(item)
            except Exception as e:
                logger.error(f"分析比赛失败 {match.get('home_team', '')} vs "
                             f"{match.get('away_team', '')}: {e}")
                results.append(self._error_item(match, str(e)))
        return results

    def _analyze_single(self, match: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        home_team = match.get('home_team', '')
        away_team = match.get('away_team', '')
        league_name = match.get('league_name', '未知联赛')

        hhad = match.get('odds', {}).get('hhad', {})
        home_odds = float(hhad.get('h', 2.0))
        draw_odds = float(hhad.get('d', 3.2))
        away_odds = float(hhad.get('a', 2.8))

        prompt = ANALYSIS_PROMPT_TEMPLATE.format(
            home_team=home_team, away_team=away_team, league_name=league_name,
            home_odds=home_odds, draw_odds=draw_odds, away_odds=away_odds)

        text = self._call_with_retry(prompt)
        if not text:
            return None
        return {
            'match_id': match.get('match_id', f'match_{uuid.uuid4().hex[:8]}'),
            'home_team': home_team,
            'away_team': away_team,
            'league_name': league_name,
            'ai_analysis': text,
            'odds': {'home': home_odds, 'draw': draw_odds, 'away': away_odds},
        }

    def _error_item(self, match: Dict[str, Any], error_msg: str) -> Dict[str, Any]:
        """单场失败的兜底输出，保证批量接口不因个别失败整体报错。"""
        return {
            'match_id': match.get('match_id', f'error_{uuid.uuid4().hex[:8]}'),
            'home_team': match.get('home_team', '未知'),
            'away_team': match.get('away_team', '未知'),
            'league_name': match.get('league_name', '未知联赛'),
            'ai_analysis': f'AI分析暂时无法获取，请稍后重试。\n\n错误信息：{error_msg}',
            'odds': {'home': 2.0, 'draw': 3.2, 'away': 2.8},
        }

    def _call_with_retry(self, prompt: str) -> Optional[str]:
        """429 限流指数退避重试；其他错误线性退避。"""
        contents = [{'role': 'user', 'parts': [{'text': prompt}]}]
        for attempt in range(self.MAX_RETRIES):
            try:
                data = self.llm.generate(contents, temperature=0.7, max_tokens=1000)
                return extract_text(data).strip() or None
            except requests.HTTPError as e:
                status = e.response.status_code if e.response is not None else None
                if status == 429 and attempt < self.MAX_RETRIES - 1:
                    delay = (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f'Gemini 限流，{delay:.1f}s 后重试')
                    time.sleep(delay)
                    continue
                logger.error(f'Gemini 调用失败: {status}')
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(attempt + 1)
            except requests.exceptions.Timeout:
                logger.warning(f'请求超时（第 {attempt + 1} 次）')
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(attempt + 1)
            except Exception as e:  # pragma: no cover
                logger.error(f'调用大模型异常: {e}')
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(attempt + 1)
        return None

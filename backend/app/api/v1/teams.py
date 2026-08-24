"""五大联赛球队基础数据。"""
from fastapi import APIRouter

from app.core.response import ok

router = APIRouter(prefix='/api/v1/teams', tags=['五大联赛-球队'])

LEAGUES = {
    'PL': '英超',
    'PD': '西甲',
    'SA': '意甲',
    'BL1': '德甲',
    'FL1': '法甲',
}

TEAMS_DATA = {
    'PL': ['Arsenal FC', 'Manchester City FC', 'Liverpool FC', 'Manchester United FC',
           'Chelsea FC', 'Tottenham Hotspur FC', 'Newcastle United FC', 'Brighton & Hove Albion FC'],
    'PD': ['Real Madrid CF', 'FC Barcelona', 'Atlético de Madrid', 'Sevilla FC',
           'Valencia CF', 'Real Betis Balompié', 'Real Sociedad de Fútbol', 'Athletic Club'],
    'SA': ['FC Internazionale Milano', 'AC Milan', 'Juventus FC', 'SSC Napoli',
           'AS Roma', 'SS Lazio', 'Atalanta BC', 'ACF Fiorentina'],
    'BL1': ['FC Bayern München', 'Borussia Dortmund', 'RB Leipzig', 'Bayer 04 Leverkusen',
            'VfB Stuttgart', 'Eintracht Frankfurt', 'VfL Wolfsburg', 'SC Freiburg'],
    'FL1': ['Paris Saint-Germain FC', 'Olympique de Marseille', 'AS Monaco FC', 'Olympique Lyonnais',
            'OGC Nice', 'Stade Rennais FC', 'RC Lens', 'LOSC Lille'],
}


@router.get('')
def get_teams():
    return ok({'leagues': LEAGUES, 'teams': TEAMS_DATA}, '球队数据获取成功')

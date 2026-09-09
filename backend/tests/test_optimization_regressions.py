"""本地优化回归测试，不提交。禁止真实数据库和模型调用。"""
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
import hashlib
import json

import pytest

from app.infrastructure.repositories import UserRepository
from app.pl_data import repository
from app.services.auth import verify_password, user_payload
from app.services.prediction import simple_predict
from ai_service.predictor import FootballAiPredictor


@pytest.mark.parametrize('values', [None, {'h': 'nan', 'd': '3', 'a': '4'},
                                     {'h': 'inf', 'd': '3', 'a': '4'}])
def test_invalid_lottery_odds_never_use_defaults(values):
    with pytest.raises(ValueError):
        simple_predict([{'odds': {'hhad': values}}])


def test_lottery_odds_are_preserved_and_change_predictions():
    result = simple_predict([{'odds': {'hhad': {'h': '4', 'd': '4', 'a': '2'}}}])[0]
    assert result['odds'] == {'home': 4, 'draw': 4, 'away': 2}
    assert result['recommendation'] == '客胜'
    assert result['probabilities']['away'] == 0.5


@pytest.mark.parametrize('market', [{'type': 'hhad'}, {'goal_line': '-1'}])
def test_handicap_market_is_not_presented_as_normal_result(market):
    with pytest.raises(ValueError, match='非让球赔率'):
        simple_predict([{'odds': {**market, 'hhad': {'h': 2, 'd': 3, 'a': 4}}}])


class Cursor:
    def __init__(self, row):
        self.row = row
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execute(self, sql, params=()):
        assert sql.count('%s') == len(params)
        self.calls.append((sql, params))

    def fetchone(self):
        return self.row


class Db:
    def __init__(self, row):
        self.db_cursor = Cursor(row)

    @contextmanager
    def connection(self):
        yield self

    def cursor(self, **kwargs):
        return self.db_cursor


def test_real_repository_upgrades_legacy_password_after_verification():
    old_hash = hashlib.sha256(b'secret123').hexdigest()
    db = Db({'id': 1, 'username': 'tester', 'password_hash': old_hash})
    repo = UserRepository(db)
    assert repo.authenticate('tester', 'wrong') is None
    assert len(db.db_cursor.calls) == 1
    result = repo.authenticate('tester', 'secret123')
    assert 'password_hash' not in result
    upgrades = [(sql, params) for sql, params in db.db_cursor.calls if 'SET password_hash' in sql]
    assert len(upgrades) == 1
    new_hash, user_id, expected_old_hash = upgrades[0][1]
    assert verify_password('secret123', new_hash)
    assert expected_old_hash == old_hash and user_id == 1
    assert len(new_hash) <= 255


def test_real_repository_reservation_failure_and_refund_date():
    db = Db(None)
    repo = UserRepository(db)
    assert repo.consume_prediction(7, 2) is None
    repo.release_prediction(7, '2026-09-08', 2)
    sql, params = db.db_cursor.calls[-1]
    assert params == ('2026-09-08', 2, 2, 7)
    assert 'WHEN last_prediction_date = %s' in sql
    with pytest.raises(ValueError):
        repo.consume_prediction(7, 0)


def test_empty_ai_answer_is_explicit_failure(monkeypatch):
    predictor = FootballAiPredictor(object())
    monkeypatch.setattr(predictor, '_call_with_retry', lambda prompt: None)
    result = predictor.analyze_matches([{'home_team': 'A', 'away_team': 'B',
                                        'home_odds': 4, 'draw_odds': 4, 'away_odds': 2}])
    assert len(result) == 1 and result[0]['status'] == 'error'
    assert result[0]['odds']['away'] == 2


def test_team_stats_numeric_values_can_enter_agent_json(monkeypatch):
    def query(sql, params):
        assert sql.count('%s') == len(params)
        return [{'played': 3, 'wins': 2, 'home_goals_scored': Decimal('1.333333')}]
    monkeypatch.setattr(repository, 'query', query)
    stats = repository.get_team_stats('Arsenal')
    assert stats['played'] == 3 and stats['wins'] == 2
    assert json.loads(json.dumps(stats))['home_goals_scored'] == 1.33


def test_expired_membership_is_not_displayed_as_premium():
    user = {'username': 'tester', 'user_type': 'premium', 'membership_expires': '2020-01-01',
            'daily_predictions_used': 3, 'total_predictions': 3}
    assert user_payload(user)['user_type'] == 'free'

from app.services.prediction import simple_predict


def test_simple_predict_normalizes_probabilities():
    result = simple_predict([{
        'home_team': 'A',
        'away_team': 'B',
        'home_odds': 2,
        'draw_odds': 4,
        'away_odds': 4,
    }])[0]

    assert result['recommendation'] == '主胜'
    assert sum(result['probabilities'].values()) == 1.0


def test_simple_predict_rejects_non_positive_odds():
    try:
        simple_predict([{'home_odds': 0, 'draw_odds': 3, 'away_odds': 3}])
    except ValueError as exc:
        assert str(exc) == '赔率必须大于0'
    else:
        raise AssertionError('应拒绝非正赔率')

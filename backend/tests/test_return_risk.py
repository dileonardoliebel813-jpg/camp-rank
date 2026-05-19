from app.scoring.return_risk import (
    calculate_return_protection_score,
    calculate_return_risk_cost,
    calculate_return_risk_score,
    map_return_risk_rate,
)


def test_return_protection_score_calculation():
    score = calculate_return_protection_score(True, True, False, True, 80, True)
    assert score == 78


def test_return_risk_score_calculation():
    score = calculate_return_risk_score(0.5, 0.4, 0.3, 0.2, 0.1)
    assert score == 35


def test_return_risk_cost_calculation():
    assert map_return_risk_rate(72) == 0.30
    assert calculate_return_risk_cost(500, 72) == 150


def test_high_return_risk_has_higher_cost():
    assert calculate_return_risk_cost(500, 80) > calculate_return_risk_cost(500, 10)


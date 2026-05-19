from app.scoring.price_calculation import (
    calculate_coupon_uncertainty_cost,
    calculate_stable_final_price,
    calculate_theoretical_lowest_price,
)


def test_stable_final_price_calculation():
    assert calculate_stable_final_price(500, 30, 20, 50, 10) == 410


def test_theoretical_lowest_price_calculation():
    assert calculate_theoretical_lowest_price(500, 30, 20, 40, 15, 5, 50, 10) == 350


def test_coupon_uncertainty_cost_calculation():
    assert calculate_coupon_uncertainty_cost(410, 350, 0.75) == 15


def test_prices_and_uncertainty_are_not_negative():
    assert calculate_stable_final_price(50, 100, 100, 100, 0) == 0
    assert calculate_theoretical_lowest_price(50, 100, 100, 100, 100, 100, 100, 0) == 0
    assert calculate_coupon_uncertainty_cost(100, 150, 0.5) == 0


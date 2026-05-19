from app.scoring.gift_value import (
    calculate_gift_adjusted_cost,
    calculate_gift_usefulness_score,
    estimate_gift_value,
)


def test_common_tent_gifts_get_conservative_values():
    assert estimate_gift_value(["防潮垫", "地钉", "营绳", "收纳袋"]) == 105


def test_unclear_gift_package_is_not_overvalued():
    assert estimate_gift_value("商家宣传价值399元大礼包") == 20


def test_gift_adjusted_cost_uses_half_gift_value():
    assert calculate_gift_adjusted_cost(500, 100) == 450
    assert calculate_gift_adjusted_cost(20, 100) == 0


def test_gift_usefulness_scores_related_items_higher():
    assert calculate_gift_usefulness_score(["防潮垫", "地钉", "营绳"]) > calculate_gift_usefulness_score(["随机贴纸"])


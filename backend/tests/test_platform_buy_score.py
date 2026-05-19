from app.scoring.platform_buy_score import (
    calculate_platform_buy_score,
    calculate_price_advantage_score,
    select_lowest_price_offer,
    select_recommended_offer,
)


def test_lowest_price_platform_identification():
    offers = [
        {"platform": "JD", "stable_final_price": 520, "risk_adjusted_cost": 520},
        {"platform": "PDD", "stable_final_price": 470, "risk_adjusted_cost": 610},
    ]
    assert select_lowest_price_offer(offers)["platform"] == "PDD"


def test_recommended_platform_can_differ_from_lowest_price():
    offers = [
        {"platform": "PDD", "stable_final_price": 470, "platform_buy_score": 58, "risk_adjusted_cost": 620},
        {"platform": "JD", "stable_final_price": 520, "platform_buy_score": 82, "risk_adjusted_cost": 535},
    ]
    assert select_lowest_price_offer(offers)["platform"] == "PDD"
    assert select_recommended_offer(offers)["platform"] == "JD"


def test_pdd_lowest_but_jd_recommended_when_return_risk_is_high():
    pdd_price_score = calculate_price_advantage_score(450, 450, 520)
    jd_price_score = calculate_price_advantage_score(520, 450, 520)
    pdd_score = calculate_platform_buy_score(pdd_price_score, 0.35, 50, 20, 30, 45, 60)
    jd_score = calculate_platform_buy_score(jd_price_score, 0.9, 60, 95, 90, 92, 85)
    assert pdd_score < jd_score


def test_lowest_price_preference_increases_price_weight():
    balanced = calculate_platform_buy_score(100, 0.7, 40, 40, 40, 40, 80, "balanced")
    lowest_price = calculate_platform_buy_score(100, 0.7, 40, 40, 40, 40, 80, "lowest_price")
    assert lowest_price > balanced


def test_after_sale_preference_increases_return_and_service_weight():
    balanced = calculate_platform_buy_score(20, 0.7, 40, 95, 95, 70, 80, "balanced")
    after_sale = calculate_platform_buy_score(20, 0.7, 40, 95, 95, 70, 80, "after_sale")
    assert after_sale > balanced


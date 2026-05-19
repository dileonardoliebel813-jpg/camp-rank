from app.scoring.product_scoring import (
    BASE_WEIGHTS,
    calculate_data_confidence_score,
    calculate_final_product_score,
    calculate_risk_penalty,
)


def test_final_product_score_calculation_with_balanced_formula():
    values = {
        "waterproof_score": 80,
        "windproof_score": 70,
        "space_score": 60,
        "portable_score": 50,
        "setup_score": 90,
        "durability_score": 75,
        "price_value_score": 85,
        "platform_benefit_score": 65,
        "return_after_sale_score": 88,
        "redbook_score": 55,
    }
    expected = round(sum(values[key] * weight for key, weight in BASE_WEIGHTS.items()) - 5, 2)
    assert calculate_final_product_score(**values, risk_penalty=5, scenario="balanced") == expected


def test_scenario_weights_take_effect():
    common = dict(
        waterproof_score=70,
        windproof_score=70,
        space_score=70,
        portable_score=95,
        setup_score=60,
        durability_score=70,
        price_value_score=60,
        platform_benefit_score=60,
        return_after_sale_score=60,
        redbook_score=60,
    )
    hiking = calculate_final_product_score(**common, scenario="hiking_lightweight")
    family = calculate_final_product_score(**common, scenario="family_camping")
    assert hiking != family
    assert hiking > family


def test_risk_penalty_takes_effect():
    assert calculate_risk_penalty(["漏水风险", "退货高风险", "空间虚标"]) == 37
    with_penalty = calculate_final_product_score(90, 90, 90, 90, 90, 90, 90, 90, 90, 90, risk_penalty=20)
    without_penalty = calculate_final_product_score(90, 90, 90, 90, 90, 90, 90, 90, 90, 90)
    assert with_penalty == without_penalty - 20


def test_data_confidence_score_is_low_when_data_is_sparse():
    sparse = calculate_data_confidence_score(
        spec_completeness=0.2,
        valid_comment_count=1,
        suspected_fake_ratio=0.8,
        platform_price_count=1,
        return_field_completeness=0.1,
        redbook_note_count=0,
        updated_recently=False,
    )
    rich = calculate_data_confidence_score(
        spec_completeness=1,
        valid_comment_count=80,
        suspected_fake_ratio=0,
        platform_price_count=4,
        return_field_completeness=1,
        redbook_note_count=8,
        updated_recently=True,
    )
    assert sparse < 30
    assert rich == 100


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(float(value), high))


BASE_WEIGHTS = {
    "waterproof_score": 0.17,
    "windproof_score": 0.13,
    "space_score": 0.11,
    "portable_score": 0.09,
    "setup_score": 0.08,
    "durability_score": 0.08,
    "price_value_score": 0.12,
    "platform_benefit_score": 0.07,
    "return_after_sale_score": 0.10,
    "redbook_score": 0.05,
}


SCENARIO_WEIGHTS = {
    "balanced": BASE_WEIGHTS,
    "newbie_weekend": {
        "waterproof_score": 0.15,
        "windproof_score": 0.10,
        "space_score": 0.11,
        "portable_score": 0.07,
        "setup_score": 0.12,
        "durability_score": 0.07,
        "price_value_score": 0.15,
        "platform_benefit_score": 0.07,
        "return_after_sale_score": 0.12,
        "redbook_score": 0.04,
    },
    "overnight": {
        "waterproof_score": 0.22,
        "windproof_score": 0.17,
        "space_score": 0.12,
        "portable_score": 0.07,
        "setup_score": 0.06,
        "durability_score": 0.10,
        "price_value_score": 0.09,
        "platform_benefit_score": 0.05,
        "return_after_sale_score": 0.07,
        "redbook_score": 0.05,
    },
    "hiking_lightweight": {
        "waterproof_score": 0.17,
        "windproof_score": 0.15,
        "space_score": 0.07,
        "portable_score": 0.22,
        "setup_score": 0.08,
        "durability_score": 0.08,
        "price_value_score": 0.10,
        "platform_benefit_score": 0.04,
        "return_after_sale_score": 0.05,
        "redbook_score": 0.04,
    },
    "family_camping": {
        "waterproof_score": 0.14,
        "windproof_score": 0.14,
        "space_score": 0.20,
        "portable_score": 0.04,
        "setup_score": 0.11,
        "durability_score": 0.11,
        "price_value_score": 0.09,
        "platform_benefit_score": 0.06,
        "return_after_sale_score": 0.08,
        "redbook_score": 0.03,
    },
}


RISK_PENALTIES = {
    "漏水风险": 15,
    "leak": 15,
    "杆子断/结构倒塌": 15,
    "broken_pole": 15,
    "collapse": 15,
    "退货高风险": 12,
    "return_high_risk": 12,
    "空间虚标": 10,
    "space_overclaim": 10,
    "严重异味": 8,
    "odor": 8,
    "疑似刷评过高": 8,
    "fake_review_high": 8,
    "数据置信度低": 8,
    "low_data_confidence": 8,
}


def calculate_dimension_score(param_score: float, comment_score: float, param_weight: float = 0.6) -> float:
    weight = max(0.0, min(float(param_weight), 1.0))
    return round(_clamp(weight * param_score + (1 - weight) * comment_score), 2)


def calculate_comment_score_from_negative_rate(weighted_negative_rate: float) -> float:
    return round(_clamp(100 - _clamp(weighted_negative_rate, 0, 1) * 100), 2)


def calculate_final_product_score(
    waterproof_score: float,
    windproof_score: float,
    space_score: float,
    portable_score: float,
    setup_score: float,
    durability_score: float,
    price_value_score: float,
    platform_benefit_score: float,
    return_after_sale_score: float,
    redbook_score: float,
    risk_penalty: float = 0,
    scenario: str = "newbie_weekend",
) -> float:
    weights = SCENARIO_WEIGHTS.get(scenario, SCENARIO_WEIGHTS["newbie_weekend"])
    values = {
        "waterproof_score": waterproof_score,
        "windproof_score": windproof_score,
        "space_score": space_score,
        "portable_score": portable_score,
        "setup_score": setup_score,
        "durability_score": durability_score,
        "price_value_score": price_value_score,
        "platform_benefit_score": platform_benefit_score,
        "return_after_sale_score": return_after_sale_score,
        "redbook_score": redbook_score,
    }
    score = sum(_clamp(values[key]) * weight for key, weight in weights.items()) - max(risk_penalty, 0)
    return round(_clamp(score), 2)


def calculate_data_confidence_score(
    spec_completeness: float,
    valid_comment_count: int,
    suspected_fake_ratio: float,
    platform_price_count: int,
    return_field_completeness: float,
    redbook_note_count: int,
    updated_recently: bool,
) -> float:
    spec_ratio = _clamp(spec_completeness, 0, 1) if spec_completeness <= 1 else _clamp(spec_completeness) / 100
    return_ratio = (
        _clamp(return_field_completeness, 0, 1)
        if return_field_completeness <= 1
        else _clamp(return_field_completeness) / 100
    )
    score = 0.0
    score += 20 * spec_ratio
    score += 20 * min(max(valid_comment_count, 0) / 50, 1)
    score += 20 * (1 - _clamp(suspected_fake_ratio, 0, 1))
    score += 15 * min(max(platform_price_count, 0) / 3, 1)
    score += 15 * return_ratio
    score += 10 * min(max(redbook_note_count, 0) / 5, 1)
    score += 20 if updated_recently else 0
    return round(_clamp(score), 2)


def calculate_risk_penalty(risk_tags: list[str]) -> float:
    total = 0.0
    seen = set()
    for tag in risk_tags:
        normalized = str(tag).strip()
        if normalized in seen:
            continue
        seen.add(normalized)
        for keyword, penalty in RISK_PENALTIES.items():
            if keyword.lower() in normalized.lower():
                total += penalty
                break
    return round(total, 2)


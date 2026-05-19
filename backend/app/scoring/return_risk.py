def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(float(value), high))


def _bool_score(value: bool) -> float:
    return 100.0 if value else 0.0


def calculate_return_protection_score(
    return_7_days: bool,
    return_shipping_insurance: bool,
    quality_issue_free_return: bool,
    fast_refund: bool,
    return_policy_clarity: float,
    official_or_self_operated: bool,
) -> float:
    score = (
        0.25 * _bool_score(return_7_days)
        + 0.20 * _bool_score(return_shipping_insurance)
        + 0.20 * _bool_score(quality_issue_free_return)
        + 0.15 * _bool_score(fast_refund)
        + 0.10 * _clamp(return_policy_clarity)
        + 0.10 * _bool_score(official_or_self_operated)
    )
    return round(_clamp(score), 2)


def calculate_return_risk_score(
    return_difficulty_rate: float,
    refund_amount_issue_rate: float,
    refund_speed_issue_rate: float,
    shipping_fee_dispute_rate: float,
    bad_customer_service_rate: float,
) -> float:
    score = (
        0.30 * _clamp(return_difficulty_rate, 0, 1)
        + 0.25 * _clamp(refund_amount_issue_rate, 0, 1)
        + 0.20 * _clamp(refund_speed_issue_rate, 0, 1)
        + 0.15 * _clamp(shipping_fee_dispute_rate, 0, 1)
        + 0.10 * _clamp(bad_customer_service_rate, 0, 1)
    ) * 100
    return round(_clamp(score), 2)


def map_return_risk_rate(return_risk_score: float) -> float:
    score = float(return_risk_score)
    if score < 15:
        return 0.02
    if score < 30:
        return 0.05
    if score < 50:
        return 0.10
    if score < 70:
        return 0.18
    return 0.30


def calculate_return_risk_cost(stable_final_price: float, return_risk_score: float) -> float:
    return round(max(stable_final_price, 0.0) * map_return_risk_rate(return_risk_score), 2)


def calculate_risk_adjusted_cost(
    stable_final_price: float,
    gift_estimated_value: float,
    coupon_uncertainty_cost: float,
    return_risk_cost: float,
    service_dispute_cost: float = 0,
) -> float:
    value = (
        stable_final_price
        - 0.5 * gift_estimated_value
        + coupon_uncertainty_cost
        + return_risk_cost
        + service_dispute_cost
    )
    return round(max(value, 0.0), 2)


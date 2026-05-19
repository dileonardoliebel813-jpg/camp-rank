def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(float(value), high))


PREFERENCE_WEIGHTS = {
    "balanced": {
        "price_advantage_score": 0.30,
        "coupon_reliability_score": 0.15,
        "gift_usefulness_score": 0.10,
        "return_protection_score": 0.20,
        "after_sale_service_score": 0.10,
        "shop_reputation_score": 0.10,
        "data_confidence_score": 0.05,
    },
    "lowest_price": {
        "price_advantage_score": 0.45,
        "coupon_reliability_score": 0.13,
        "gift_usefulness_score": 0.07,
        "return_protection_score": 0.13,
        "after_sale_service_score": 0.07,
        "shop_reputation_score": 0.08,
        "data_confidence_score": 0.07,
    },
    "after_sale": {
        "price_advantage_score": 0.20,
        "coupon_reliability_score": 0.10,
        "gift_usefulness_score": 0.06,
        "return_protection_score": 0.30,
        "after_sale_service_score": 0.18,
        "shop_reputation_score": 0.10,
        "data_confidence_score": 0.06,
    },
    "gift_package": {
        "price_advantage_score": 0.24,
        "coupon_reliability_score": 0.12,
        "gift_usefulness_score": 0.24,
        "return_protection_score": 0.16,
        "after_sale_service_score": 0.08,
        "shop_reputation_score": 0.09,
        "data_confidence_score": 0.07,
    },
}


def calculate_price_advantage_score(price: float, min_price: float, max_price: float) -> float:
    if max_price <= min_price:
        return 100.0
    score = (max_price - price) / (max_price - min_price) * 100
    return round(_clamp(score), 2)


def _coupon_to_100(score: float) -> float:
    score = float(score)
    return score * 100 if score <= 1 else score


def calculate_platform_buy_score(
    price_advantage_score: float,
    coupon_reliability_score: float,
    gift_usefulness_score: float,
    return_protection_score: float,
    after_sale_service_score: float,
    shop_reputation_score: float,
    data_confidence_score: float,
    user_preference: str = "balanced",
) -> float:
    weights = PREFERENCE_WEIGHTS.get(user_preference, PREFERENCE_WEIGHTS["balanced"])
    values = {
        "price_advantage_score": _clamp(price_advantage_score),
        "coupon_reliability_score": _clamp(_coupon_to_100(coupon_reliability_score)),
        "gift_usefulness_score": _clamp(gift_usefulness_score),
        "return_protection_score": _clamp(return_protection_score),
        "after_sale_service_score": _clamp(after_sale_service_score),
        "shop_reputation_score": _clamp(shop_reputation_score),
        "data_confidence_score": _clamp(data_confidence_score),
    }
    return round(sum(values[key] * weight for key, weight in weights.items()), 2)


def select_lowest_price_offer(offers: list[dict]) -> dict:
    if not offers:
        return {}
    return min(offers, key=lambda offer: (offer.get("stable_final_price", float("inf")), offer.get("risk_adjusted_cost", float("inf"))))


def _score_offer(offer: dict, user_preference: str) -> float:
    if all(
        key in offer
        for key in [
            "price_advantage_score",
            "coupon_reliability_score",
            "gift_usefulness_score",
            "return_protection_score",
            "after_sale_service_score",
            "shop_reputation_score",
            "data_confidence_score",
        ]
    ):
        return calculate_platform_buy_score(user_preference=user_preference, **{
            key: offer[key]
            for key in [
                "price_advantage_score",
                "coupon_reliability_score",
                "gift_usefulness_score",
                "return_protection_score",
                "after_sale_service_score",
                "shop_reputation_score",
                "data_confidence_score",
            ]
        })
    return float(offer.get("platform_buy_score", 0.0))


def select_recommended_offer(offers: list[dict], user_preference: str = "balanced") -> dict:
    if not offers:
        return {}
    return max(
        offers,
        key=lambda offer: (
            _score_offer(offer, user_preference),
            -float(offer.get("risk_adjusted_cost", float("inf"))),
            -float(offer.get("stable_final_price", float("inf"))),
        ),
    )


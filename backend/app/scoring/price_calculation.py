def _non_negative(value: float) -> float:
    return round(max(float(value), 0.0), 2)


def calculate_stable_final_price(
    current_price: float,
    shop_coupon_amount: float = 0,
    platform_coupon_amount: float = 0,
    discount_amount: float = 0,
    shipping_fee: float = 0,
) -> float:
    value = (
        current_price
        - shop_coupon_amount
        - platform_coupon_amount
        - discount_amount
        + shipping_fee
    )
    return _non_negative(value)


def calculate_theoretical_lowest_price(
    current_price: float,
    shop_coupon_amount: float = 0,
    platform_coupon_amount: float = 0,
    member_coupon_amount: float = 0,
    limited_coupon_amount: float = 0,
    red_packet_amount: float = 0,
    discount_amount: float = 0,
    shipping_fee: float = 0,
) -> float:
    value = (
        current_price
        - shop_coupon_amount
        - platform_coupon_amount
        - member_coupon_amount
        - limited_coupon_amount
        - red_packet_amount
        - discount_amount
        + shipping_fee
    )
    return _non_negative(value)


def calculate_coupon_uncertainty_cost(
    stable_final_price: float,
    theoretical_lowest_price: float,
    coupon_reliability_score: float,
) -> float:
    reliability = max(0.0, min(float(coupon_reliability_score), 1.0))
    value = (stable_final_price - theoretical_lowest_price) * (1 - reliability)
    return _non_negative(value)


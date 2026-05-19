from pydantic import BaseModel


class PriceCompareOffer(BaseModel):
    platform: str
    shop_name: str
    stable_final_price: float
    theoretical_lowest_price: float
    coupon_reliability_score: float
    gift_estimated_value: float
    gift_adjusted_cost: float
    return_protection_score: float
    return_risk_score: float
    return_risk_cost: float
    risk_adjusted_cost: float
    platform_buy_score: float
    is_lowest_price: bool
    is_recommended_platform: bool
    warning_tags: list[str]

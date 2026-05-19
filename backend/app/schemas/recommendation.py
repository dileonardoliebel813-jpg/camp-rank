from pydantic import BaseModel


class MockRecommendation(BaseModel):
    product_name: str
    final_score: float
    data_confidence_score: float
    recommended_platform: str | None
    lowest_price_platform: str | None
    price_gap: float
    reason: str
    advantages: list[str]
    risks: list[str]
    risk_tags: list[str]

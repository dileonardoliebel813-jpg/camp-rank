from pydantic import BaseModel


class ProductListItem(BaseModel):
    id: int
    normalized_name: str
    brand: str
    model_name: str
    capacity: str
    use_case: str
    final_score: float | None
    data_confidence_score: float
    min_stable_final_price: float | None
    max_stable_final_price: float | None
    recommended_platform: str | None
    lowest_price_platform: str | None
    main_risk_tags: list[str]

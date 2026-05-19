from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.product import TimestampMixin


class ProductScore(Base, TimestampMixin):
    __tablename__ = "product_scores"

    id = __import__("sqlalchemy").Column(Integer, primary_key=True, index=True)
    canonical_product_id = __import__("sqlalchemy").Column(Integer, ForeignKey("canonical_products.id"), nullable=False, unique=True)
    waterproof_score = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    windproof_score = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    space_score = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    portable_score = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    setup_score = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    durability_score = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    price_value_score = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    platform_benefit_score = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    return_after_sale_score = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    redbook_score = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    data_confidence_score = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    risk_penalty = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    final_score = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False, index=True)
    recommend_level = __import__("sqlalchemy").Column(String(50), nullable=False)

    canonical_product = relationship("CanonicalProduct", back_populates="product_score")

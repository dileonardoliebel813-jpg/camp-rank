from sqlalchemy import Boolean, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.product import TimestampMixin


class PlatformOfferAnalysis(Base, TimestampMixin):
    __tablename__ = "platform_offer_analyses"

    id = __import__("sqlalchemy").Column(Integer, primary_key=True, index=True)
    product_id = __import__("sqlalchemy").Column(Integer, ForeignKey("products.id"), nullable=False, unique=True)
    gift_adjusted_cost = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    coupon_uncertainty_cost = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    risk_adjusted_cost = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    platform_buy_score = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    is_lowest_price = __import__("sqlalchemy").Column(Boolean, default=False, nullable=False)
    is_recommended_platform = __import__("sqlalchemy").Column(Boolean, default=False, nullable=False)
    recommendation_reason = __import__("sqlalchemy").Column(Text, nullable=True)
    warning_tags = __import__("sqlalchemy").Column(Text, nullable=True)

    product = relationship("Product", back_populates="platform_offer_analysis")

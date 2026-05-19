from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class CanonicalProduct(Base, TimestampMixin):
    __tablename__ = "canonical_products"

    id = Integer().with_variant(Integer, "sqlite")
    id = __import__("sqlalchemy").Column(id, primary_key=True, index=True)
    normalized_name = __import__("sqlalchemy").Column(String(255), unique=True, nullable=False, index=True)
    brand = __import__("sqlalchemy").Column(String(100), nullable=False, index=True)
    model_name = __import__("sqlalchemy").Column(String(100), nullable=False)
    capacity = __import__("sqlalchemy").Column(String(50), nullable=False)
    use_case = __import__("sqlalchemy").Column(String(100), nullable=False, index=True)
    main_image_url = __import__("sqlalchemy").Column(String(500), nullable=True)
    match_confidence = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    data_confidence_score = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)

    products = relationship("Product", back_populates="canonical_product", cascade="all, delete-orphan")
    redbook_notes = relationship("RedBookNote", back_populates="canonical_product", cascade="all, delete-orphan")
    product_score = relationship("ProductScore", back_populates="canonical_product", uselist=False, cascade="all, delete-orphan")


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id = __import__("sqlalchemy").Column(Integer, primary_key=True, index=True)
    canonical_product_id = __import__("sqlalchemy").Column(Integer, ForeignKey("canonical_products.id"), nullable=False, index=True)
    platform = __import__("sqlalchemy").Column(String(50), nullable=False, index=True)
    platform_product_id = __import__("sqlalchemy").Column(String(100), nullable=False, index=True)
    title = __import__("sqlalchemy").Column(String(500), nullable=False)
    shop_name = __import__("sqlalchemy").Column(String(200), nullable=False)
    shop_type = __import__("sqlalchemy").Column(String(100), nullable=False)
    product_url = __import__("sqlalchemy").Column(String(500), nullable=True)
    image_url = __import__("sqlalchemy").Column(String(500), nullable=True)
    sales_volume = __import__("sqlalchemy").Column(Integer, default=0, nullable=False)
    rating_count = __import__("sqlalchemy").Column(Integer, default=0, nullable=False)
    positive_rate = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)

    canonical_product = relationship("CanonicalProduct", back_populates="products")
    spec = relationship("ProductSpec", back_populates="product", uselist=False, cascade="all, delete-orphan")
    benefit = relationship("ProductBenefit", back_populates="product", uselist=False, cascade="all, delete-orphan")
    return_policy = relationship("ReturnPolicyAnalysis", back_populates="product", uselist=False, cascade="all, delete-orphan")
    prices = relationship("ProductPrice", back_populates="product", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="product", cascade="all, delete-orphan")
    platform_offer_analysis = relationship("PlatformOfferAnalysis", back_populates="product", uselist=False, cascade="all, delete-orphan")


class ProductSpec(Base, TimestampMixin):
    __tablename__ = "product_specs"

    id = __import__("sqlalchemy").Column(Integer, primary_key=True, index=True)
    product_id = __import__("sqlalchemy").Column(Integer, ForeignKey("products.id"), nullable=False, unique=True)
    waterproof_index_outer = __import__("sqlalchemy").Column(Integer, nullable=True)
    waterproof_index_floor = __import__("sqlalchemy").Column(Integer, nullable=True)
    weight_kg = __import__("sqlalchemy").Column(Float, nullable=True)
    expanded_length_cm = __import__("sqlalchemy").Column(Float, nullable=True)
    expanded_width_cm = __import__("sqlalchemy").Column(Float, nullable=True)
    expanded_height_cm = __import__("sqlalchemy").Column(Float, nullable=True)
    floor_area_m2 = __import__("sqlalchemy").Column(Float, nullable=True)
    packed_volume_l = __import__("sqlalchemy").Column(Float, nullable=True)
    pole_material = __import__("sqlalchemy").Column(String(100), nullable=True)
    outer_material = __import__("sqlalchemy").Column(String(200), nullable=True)
    setup_type = __import__("sqlalchemy").Column(String(100), nullable=True)
    tent_type = __import__("sqlalchemy").Column(String(100), nullable=True)
    raw_specs_json = __import__("sqlalchemy").Column(Text, nullable=True)

    product = relationship("Product", back_populates="spec")


class ProductPrice(Base, TimestampMixin):
    __tablename__ = "product_prices"

    id = __import__("sqlalchemy").Column(Integer, primary_key=True, index=True)
    product_id = __import__("sqlalchemy").Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    original_price = __import__("sqlalchemy").Column(Float, nullable=False)
    current_price = __import__("sqlalchemy").Column(Float, nullable=False)
    shop_coupon_amount = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    platform_coupon_amount = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    member_coupon_amount = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    limited_coupon_amount = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    red_packet_amount = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    discount_amount = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    shipping_fee = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    stable_final_price = __import__("sqlalchemy").Column(Float, nullable=False, index=True)
    theoretical_lowest_price = __import__("sqlalchemy").Column(Float, nullable=False)
    coupon_reliability_score = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    coupon_text = __import__("sqlalchemy").Column(Text, nullable=True)
    promotion_text = __import__("sqlalchemy").Column(Text, nullable=True)
    price_update_time = __import__("sqlalchemy").Column(DateTime, default=utcnow, nullable=False)

    product = relationship("Product", back_populates="prices")


class ProductBenefit(Base, TimestampMixin):
    __tablename__ = "product_benefits"

    id = __import__("sqlalchemy").Column(Integer, primary_key=True, index=True)
    product_id = __import__("sqlalchemy").Column(Integer, ForeignKey("products.id"), nullable=False, unique=True)
    free_shipping = __import__("sqlalchemy").Column(Boolean, default=False, nullable=False)
    shipping_insurance = __import__("sqlalchemy").Column(Boolean, default=False, nullable=False)
    return_7_days = __import__("sqlalchemy").Column(Boolean, default=False, nullable=False)
    fast_refund = __import__("sqlalchemy").Column(Boolean, default=False, nullable=False)
    price_protection = __import__("sqlalchemy").Column(Boolean, default=False, nullable=False)
    official_store = __import__("sqlalchemy").Column(Boolean, default=False, nullable=False)
    self_operated = __import__("sqlalchemy").Column(Boolean, default=False, nullable=False)
    gift_items = __import__("sqlalchemy").Column(Text, nullable=True)
    gift_estimated_value = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    gift_usefulness_score = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    platform_benefit_score = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)

    product = relationship("Product", back_populates="benefit")


class ReturnPolicyAnalysis(Base, TimestampMixin):
    __tablename__ = "return_policy_analyses"

    id = __import__("sqlalchemy").Column(Integer, primary_key=True, index=True)
    product_id = __import__("sqlalchemy").Column(Integer, ForeignKey("products.id"), nullable=False, unique=True)
    return_shipping_insurance = __import__("sqlalchemy").Column(Boolean, default=False, nullable=False)
    return_shipping_payer = __import__("sqlalchemy").Column(String(100), nullable=True)
    return_condition_text = __import__("sqlalchemy").Column(Text, nullable=True)
    opened_return_allowed = __import__("sqlalchemy").Column(Boolean, default=False, nullable=False)
    used_return_allowed = __import__("sqlalchemy").Column(Boolean, default=False, nullable=False)
    quality_issue_free_return = __import__("sqlalchemy").Column(Boolean, default=False, nullable=False)
    refund_speed_type = __import__("sqlalchemy").Column(String(100), nullable=True)
    refund_full_amount = __import__("sqlalchemy").Column(Boolean, default=True, nullable=False)
    partial_refund_risk = __import__("sqlalchemy").Column(Boolean, default=False, nullable=False)
    seller_return_attitude = __import__("sqlalchemy").Column(String(100), nullable=True)
    return_policy_clarity = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    return_negative_rate = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    refund_dispute_rate = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    return_protection_score = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    return_risk_score = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    return_risk_cost = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)

    product = relationship("Product", back_populates="return_policy")

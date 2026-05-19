from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.product import TimestampMixin, utcnow


class Comment(Base, TimestampMixin):
    __tablename__ = "comments"

    id = __import__("sqlalchemy").Column(Integer, primary_key=True, index=True)
    product_id = __import__("sqlalchemy").Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    platform = __import__("sqlalchemy").Column(String(50), nullable=False)
    comment_text = __import__("sqlalchemy").Column(Text, nullable=False)
    rating = __import__("sqlalchemy").Column(Float, nullable=True)
    comment_type = __import__("sqlalchemy").Column(String(50), nullable=False)
    has_image = __import__("sqlalchemy").Column(Boolean, default=False, nullable=False)
    is_follow_up = __import__("sqlalchemy").Column(Boolean, default=False, nullable=False)
    comment_time = __import__("sqlalchemy").Column(DateTime, default=utcnow, nullable=False)
    seller_reply = __import__("sqlalchemy").Column(Text, nullable=True)

    product = relationship("Product", back_populates="comments")
    quality_analysis = relationship("CommentQualityAnalysis", back_populates="comment", uselist=False, cascade="all, delete-orphan")
    negative_analysis = relationship("NegativeReviewAnalysis", back_populates="comment", uselist=False, cascade="all, delete-orphan")


class CommentQualityAnalysis(Base, TimestampMixin):
    __tablename__ = "comment_quality_analyses"

    id = __import__("sqlalchemy").Column(Integer, primary_key=True, index=True)
    comment_id = __import__("sqlalchemy").Column(Integer, ForeignKey("comments.id"), nullable=False, unique=True)
    comment_credibility_score = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    fake_review_risk_score = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    effective_comment_weight = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    is_low_information = __import__("sqlalchemy").Column(Boolean, default=False, nullable=False)
    is_suspected_fake = __import__("sqlalchemy").Column(Boolean, default=False, nullable=False)
    risk_tags = __import__("sqlalchemy").Column(Text, nullable=True)

    comment = relationship("Comment", back_populates="quality_analysis")


class NegativeReviewAnalysis(Base, TimestampMixin):
    __tablename__ = "negative_review_analyses"

    id = __import__("sqlalchemy").Column(Integer, primary_key=True, index=True)
    comment_id = __import__("sqlalchemy").Column(Integer, ForeignKey("comments.id"), nullable=False, unique=True)
    negative_type = __import__("sqlalchemy").Column(String(100), nullable=True)
    affected_dimension = __import__("sqlalchemy").Column(String(100), nullable=True)
    risk_level = __import__("sqlalchemy").Column(String(50), nullable=True)
    is_valid_negative = __import__("sqlalchemy").Column(Boolean, default=False, nullable=False)

    comment = relationship("Comment", back_populates="negative_analysis")


class RedBookNote(Base, TimestampMixin):
    __tablename__ = "redbook_notes"

    id = __import__("sqlalchemy").Column(Integer, primary_key=True, index=True)
    canonical_product_id = __import__("sqlalchemy").Column(Integer, ForeignKey("canonical_products.id"), nullable=False, index=True)
    title = __import__("sqlalchemy").Column(String(300), nullable=False)
    content = __import__("sqlalchemy").Column(Text, nullable=False)
    comments_text = __import__("sqlalchemy").Column(Text, nullable=True)
    likes = __import__("sqlalchemy").Column(Integer, default=0, nullable=False)
    favorites = __import__("sqlalchemy").Column(Integer, default=0, nullable=False)
    comment_count = __import__("sqlalchemy").Column(Integer, default=0, nullable=False)
    is_suspected_ad = __import__("sqlalchemy").Column(Boolean, default=False, nullable=False)
    credibility_score = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    sentiment_score = __import__("sqlalchemy").Column(Float, default=0.0, nullable=False)
    risk_tags = __import__("sqlalchemy").Column(Text, nullable=True)

    canonical_product = relationship("CanonicalProduct", back_populates="redbook_notes")

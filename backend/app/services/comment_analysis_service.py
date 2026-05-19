import json

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models import (
    CanonicalProduct,
    Comment,
    CommentQualityAnalysis,
    NegativeReviewAnalysis,
    Product,
    RedBookNote,
)
from app.nlp.fake_review_detector import calculate_fake_review_risk_score
from app.nlp.negative_review_classifier import classify_negative_review, is_valid_negative_review
from app.nlp.redbook_analyzer import analyze_redbook_note
from app.nlp.review_quality import calculate_comment_credibility_score, is_low_information_review
from app.nlp.weighted_metrics import calculate_effective_comment_weight, calculate_weighted_negative_rate
from app.scoring.review_evidence_score import calculate_review_evidence


SUMMARY_DIMENSIONS = [
    "waterproof",
    "windproof",
    "space",
    "storage",
    "setup",
    "smell",
    "sunproof",
    "return_after_sale",
]


def _json_list(values: list[str]) -> str:
    return json.dumps(sorted(set(values)), ensure_ascii=False)


def _parse_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
        if isinstance(value, list):
            return [str(item) for item in value]
        return [str(value)]
    except json.JSONDecodeError:
        return [item.strip() for item in raw.split(",") if item.strip()]


def _comment_type_for_weight(comment: Comment, is_low_info: bool, suspected_fake: bool, is_negative: bool) -> str:
    if suspected_fake:
        return "suspected_fake"
    if is_low_info:
        return "low_information"
    if is_negative or "差" in (comment.comment_type or ""):
        return "negative"
    if "中" in (comment.comment_type or ""):
        return "neutral"
    return "positive"


def analyze_and_update_comments(db: Session) -> dict:
    comments = db.query(Comment).options(joinedload(Comment.quality_analysis), joinedload(Comment.negative_analysis)).all()
    corpus = [comment.comment_text for comment in comments]

    for comment in comments:
        if comment.quality_analysis and comment.negative_analysis:
            continue
        negative_result = classify_negative_review(comment.comment_text)
        low_info = is_low_information_review(comment.comment_text)
        fake_risk = calculate_fake_review_risk_score(comment.comment_text, corpus)
        suspected_fake = fake_risk >= 0.65
        credibility = calculate_comment_credibility_score(comment)
        comment_type = _comment_type_for_weight(comment, low_info, suspected_fake, negative_result["is_negative"])
        effective_weight = calculate_effective_comment_weight(
            credibility,
            fake_risk,
            comment_type,
            has_image=comment.has_image,
            is_follow_up=comment.is_follow_up,
        )

        quality = comment.quality_analysis or CommentQualityAnalysis(comment_id=comment.id)
        quality.comment_credibility_score = credibility
        quality.fake_review_risk_score = fake_risk
        quality.effective_comment_weight = effective_weight
        quality.is_low_information = low_info
        quality.is_suspected_fake = suspected_fake
        quality.risk_tags = _json_list(negative_result["risk_tags"])
        db.add(quality)

        negative = comment.negative_analysis or NegativeReviewAnalysis(comment_id=comment.id)
        negative.negative_type = negative_result["negative_type"]
        negative.affected_dimension = _json_list(negative_result["affected_dimensions"])
        negative.risk_level = negative_result["risk_level"]
        negative.is_valid_negative = is_valid_negative_review(comment.comment_text)
        db.add(negative)

    db.commit()
    return {
        "comment_count": len(comments),
        "quality_analysis_count": db.query(CommentQualityAnalysis).count(),
        "negative_analysis_count": db.query(NegativeReviewAnalysis).count(),
    }


def analyze_and_update_redbook_notes(db: Session) -> dict:
    notes = db.query(RedBookNote).all()
    for note in notes:
        result = analyze_redbook_note(note.title, note.content, note.comments_text or "")
        note.is_suspected_ad = result["is_suspected_ad"]
        note.credibility_score = result["credibility_score"]
        note.sentiment_score = result["sentiment_score"]
        note.risk_tags = _json_list(result["risk_tags"])
        db.add(note)
    db.commit()
    return {"note_count": len(notes)}


def get_comment_risk_summary(db: Session, canonical_product_id: int) -> dict:
    canonical = db.query(CanonicalProduct).filter(CanonicalProduct.id == canonical_product_id).first()
    if not canonical:
        raise HTTPException(status_code=404, detail="Canonical product not found")

    products = (
        db.query(Product)
        .options(
            joinedload(Product.comments).joinedload(Comment.quality_analysis),
            joinedload(Product.comments).joinedload(Comment.negative_analysis),
        )
        .filter(Product.canonical_product_id == canonical_product_id)
        .all()
    )
    comments = [comment for product in products for comment in product.comments]
    analysis_rows = []
    high_risk_tags = []
    for comment in comments:
        quality = comment.quality_analysis
        negative = comment.negative_analysis
        dimensions = _parse_list(negative.affected_dimension if negative else None)
        risk_tags = _parse_list(quality.risk_tags if quality else None)
        if negative and negative.risk_level == "high":
            high_risk_tags.extend(risk_tags)
        analysis_rows.append(
            {
                "effective_comment_weight": quality.effective_comment_weight if quality else 0.0,
                "affected_dimensions": dimensions,
                "is_negative": bool(negative and negative.is_valid_negative),
                "risk_level": negative.risk_level if negative else "none",
            }
        )

    review_evidence = calculate_review_evidence(comments)
    summary = {
        f"{dimension}_negative_rate": calculate_weighted_negative_rate(analysis_rows, dimension)
        for dimension in SUMMARY_DIMENSIONS
    }
    summary.update(
        {
            "high_risk_tags": sorted(set(high_risk_tags)),
            "suspected_fake_review_count": sum(
                1 for comment in comments if comment.quality_analysis and comment.quality_analysis.is_suspected_fake
            ),
            "low_information_review_count": sum(
                1 for comment in comments if comment.quality_analysis and comment.quality_analysis.is_low_information
            ),
            "valid_negative_review_count": sum(
                1 for comment in comments if comment.negative_analysis and comment.negative_analysis.is_valid_negative
            ),
            "raw_review_distribution": review_evidence["raw_review_distribution"],
            "raw_review_ratio": review_evidence["raw_review_ratio"],
            "normalized_review_weights": review_evidence["normalized_review_weights"],
            "normalized_layer_risk_rates": review_evidence["normalized_layer_risk_rates"],
            "standardized_risk_rate": review_evidence["standardized_risk_rate"],
            "dimension_risk_rates": review_evidence["dimension_risk_rates"],
            "review_evidence_score": review_evidence["review_evidence_score"],
            "sampling_bias_index": review_evidence["sampling_bias_index"],
            "evidence_confidence_score": review_evidence["evidence_confidence_score"],
            "review_sample_warnings": review_evidence["review_sample_warnings"],
        }
    )
    return summary


def get_redbook_summary(db: Session, canonical_product_id: int) -> dict:
    canonical = (
        db.query(CanonicalProduct)
        .options(joinedload(CanonicalProduct.redbook_notes))
        .filter(CanonicalProduct.id == canonical_product_id)
        .first()
    )
    if not canonical:
        raise HTTPException(status_code=404, detail="Canonical product not found")

    notes = canonical.redbook_notes
    note_count = len(notes)
    if note_count == 0:
        return {
            "note_count": 0,
            "suspected_ad_count": 0,
            "average_credibility_score": 0.0,
            "average_sentiment_score": 0.0,
            "risk_tags": [],
        }
    risk_tags = []
    for note in notes:
        risk_tags.extend(_parse_list(note.risk_tags))
    return {
        "note_count": note_count,
        "suspected_ad_count": sum(1 for note in notes if note.is_suspected_ad),
        "average_credibility_score": round(sum(note.credibility_score for note in notes) / note_count, 4),
        "average_sentiment_score": round(sum(note.sentiment_score for note in notes) / note_count, 2),
        "risk_tags": sorted(set(risk_tags)),
    }

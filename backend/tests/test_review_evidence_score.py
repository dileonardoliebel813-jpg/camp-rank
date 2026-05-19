from types import SimpleNamespace

from app.scoring.review_evidence_score import (
    calculate_review_evidence,
    classify_review_layer,
    matched_risk_dimensions,
)


def _comment(text, rating=5, comment_type="positive", weight=0.5, has_image=False, is_follow_up=False):
    return SimpleNamespace(
        comment_text=text,
        rating=rating,
        comment_type=comment_type,
        has_image=has_image,
        is_follow_up=is_follow_up,
        quality_analysis=SimpleNamespace(
            effective_comment_weight=weight,
            is_low_information=False,
            is_suspected_fake=False,
            risk_tags="[]",
        ),
        negative_analysis=SimpleNamespace(
            negative_type="none",
            risk_level="none",
            affected_dimension="[]",
        ),
    )


def test_classify_review_layer_uses_rating_and_comment_type():
    assert classify_review_layer(_comment("ok", rating=5)) == "positive"
    assert classify_review_layer(_comment("一般", rating=3)) == "neutral"
    assert classify_review_layer(_comment("差", rating=1)) == "negative"
    assert classify_review_layer(_comment("type wins", rating=5, comment_type="negative")) == "negative"


def test_matches_direct_risk_dimensions_from_chinese_text():
    result = matched_risk_dimensions(_comment("下雨以后有点漏水，客服处理也比较慢", rating=2))
    assert "waterproof" in result
    assert "return_after_sale" in result


def test_review_evidence_normalizes_unbalanced_sampling():
    mostly_bad = [_comment("漏水，退货也麻烦", rating=1, comment_type="negative") for _ in range(30)]
    mostly_good = [_comment("空间挺大，搭建方便", rating=5, comment_type="positive") for _ in range(5)]
    summary = calculate_review_evidence(mostly_bad + mostly_good)
    assert summary["raw_review_distribution"]["negative"] == 30
    assert summary["normalized_review_weights"]["negative"] == 0.35
    assert summary["sampling_bias_index"] > 0.3
    assert summary["review_evidence_score"] < 90
    assert summary["evidence_confidence_score"] < 100


from app.nlp.weighted_metrics import calculate_effective_comment_weight, calculate_weighted_negative_rate


def test_suspected_fake_review_weight_is_zero():
    assert calculate_effective_comment_weight(0.8, 0.9, "suspected_fake") == 0.0


def test_image_follow_up_weight_is_higher():
    base = calculate_effective_comment_weight(0.8, 0.1, "negative")
    with_evidence = calculate_effective_comment_weight(0.8, 0.1, "negative", has_image=True, is_follow_up=True)

    assert with_evidence > base


def test_weighted_negative_rate_calculates_dimension_rate():
    rows = [
        {"effective_comment_weight": 0.8, "affected_dimensions": ["waterproof"], "is_negative": True},
        {"effective_comment_weight": 0.2, "affected_dimensions": ["waterproof"], "is_negative": False},
        {"effective_comment_weight": 1.0, "affected_dimensions": ["space"], "is_negative": True},
    ]

    assert calculate_weighted_negative_rate(rows, "waterproof") == 0.8


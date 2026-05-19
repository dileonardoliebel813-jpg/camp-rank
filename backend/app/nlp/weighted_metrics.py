COMMENT_TYPE_WEIGHTS = {
    "follow_up": 1.2,
    "image": 1.1,
    "negative": 1.1,
    "neutral": 1.0,
    "positive": 0.7,
    "low_information": 0.1,
    "suspected_fake": 0.0,
}


def _normalize_score(value: float) -> float:
    if value is None:
        return 0.0
    numeric = float(value)
    return numeric / 100 if numeric > 1 else numeric


def calculate_effective_comment_weight(
    credibility_score: float,
    fake_review_risk_score: float,
    comment_type: str,
    has_image: bool = False,
    is_follow_up: bool = False,
) -> float:
    normalized_credibility = _normalize_score(credibility_score)
    normalized_fake_risk = _normalize_score(fake_review_risk_score)
    normalized_type = (comment_type or "neutral").lower()

    if normalized_type == "suspected_fake":
        type_weight = COMMENT_TYPE_WEIGHTS["suspected_fake"]
    elif normalized_type == "low_information":
        type_weight = COMMENT_TYPE_WEIGHTS["low_information"]
    else:
        type_weight = COMMENT_TYPE_WEIGHTS.get(normalized_type, COMMENT_TYPE_WEIGHTS["neutral"])
        if has_image:
            type_weight *= COMMENT_TYPE_WEIGHTS["image"]
        if is_follow_up:
            type_weight *= COMMENT_TYPE_WEIGHTS["follow_up"]

    weight = normalized_credibility * (1 - normalized_fake_risk) * type_weight
    return round(max(0.0, weight), 4)


def calculate_weighted_negative_rate(comments_analysis: list[dict], dimension: str) -> float:
    relevant_weight = 0.0
    negative_weight = 0.0
    for item in comments_analysis:
        affected_dimensions = item.get("affected_dimensions") or []
        if isinstance(affected_dimensions, str):
            affected_dimensions = [affected_dimensions]
        weight = float(item.get("effective_comment_weight", 0.0) or 0.0)
        is_dimension_related = dimension in affected_dimensions or dimension == item.get("dimension")
        if not is_dimension_related:
            continue
        relevant_weight += weight
        if item.get("is_negative") or item.get("risk_level") in {"high", "medium", "low"}:
            negative_weight += weight
    if relevant_weight <= 0:
        return 0.0
    return round(negative_weight / relevant_weight, 4)


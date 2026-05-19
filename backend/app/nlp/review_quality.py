from app.nlp.fake_review_detector import calculate_fake_review_risk_score
from app.nlp.keyword_dict import (
    LOW_INFORMATION_KEYWORDS,
    PEOPLE_KEYWORDS,
    SCENE_KEYWORDS,
    SPECIFIC_PROBLEM_KEYWORDS,
    TENT_USAGE_KEYWORDS,
    TIME_KEYWORDS,
    WEATHER_KEYWORDS,
    WATERPROOF_NEGATIVE_KEYWORDS,
    SETUP_NEGATIVE_KEYWORDS,
    STORAGE_NEGATIVE_KEYWORDS,
)


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, round(value, 4)))


def is_low_information_review(text: str) -> bool:
    clean_text = (text or "").strip()
    if len(clean_text) < 6:
        return True
    if "还没用" in clean_text and "好评" in clean_text:
        return True
    if "先好评" in clean_text or "习惯好评" in clean_text:
        return True
    if clean_text in LOW_INFORMATION_KEYWORDS:
        return True
    if _contains_any(clean_text, LOW_INFORMATION_KEYWORDS) and not _contains_any(clean_text, TENT_USAGE_KEYWORDS):
        return True
    return False


def calculate_information_score(text: str) -> float:
    clean_text = (text or "").strip()
    if not clean_text:
        return 0.0

    score = 0.08 if len(clean_text) >= 6 else 0.0
    feature_groups = [
        WEATHER_KEYWORDS,
        PEOPLE_KEYWORDS,
        SETUP_NEGATIVE_KEYWORDS + ["搭建", "支架", "说明书"],
        STORAGE_NEGATIVE_KEYWORDS + ["收纳"],
        WATERPROOF_NEGATIVE_KEYWORDS + ["防水"],
        TIME_KEYWORDS,
        SPECIFIC_PROBLEM_KEYWORDS,
    ]
    for keywords in feature_groups:
        if _contains_any(clean_text, keywords):
            score += 0.13
    if len(clean_text) >= 25:
        score += 0.1
    if is_low_information_review(clean_text):
        score *= 0.25
    return _clamp(score)


def calculate_context_score(text: str) -> float:
    clean_text = (text or "").strip()
    if not clean_text:
        return 0.0

    score = 0.0
    for keywords in [SCENE_KEYWORDS, WEATHER_KEYWORDS, PEOPLE_KEYWORDS, TIME_KEYWORDS]:
        if _contains_any(clean_text, keywords):
            score += 0.22
    if "用了一晚" in clean_text or "周末露营" in clean_text or "一家人" in clean_text:
        score += 0.12
    return _clamp(score)


def calculate_comment_credibility_score(comment) -> float:
    text = getattr(comment, "comment_text", "") if not isinstance(comment, str) else comment
    has_image = bool(getattr(comment, "has_image", False))
    is_follow_up = bool(getattr(comment, "is_follow_up", False))

    information_score = calculate_information_score(text)
    context_score = calculate_context_score(text)
    evidence_score = 0.0
    if has_image:
        evidence_score += 0.55
    if is_follow_up:
        evidence_score += 0.45
    evidence_score = _clamp(evidence_score)
    time_distribution_score = 0.8
    non_template_score = 1 - calculate_fake_review_risk_score(text)
    multi_platform_score = 0.6

    credibility_score = (
        0.25 * information_score
        + 0.20 * context_score
        + 0.15 * evidence_score
        + 0.15 * time_distribution_score
        + 0.15 * non_template_score
        + 0.10 * multi_platform_score
    )
    return _clamp(credibility_score)


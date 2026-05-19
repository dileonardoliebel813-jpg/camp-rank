from collections import Counter
from difflib import SequenceMatcher

from app.nlp.keyword_dict import (
    LOW_INFORMATION_KEYWORDS,
    POSITIVE_GENERIC_KEYWORDS,
    REDBOOK_AD_KEYWORDS,
    SPECIFIC_PROBLEM_KEYWORDS,
    TENT_USAGE_KEYWORDS,
    WEATHER_KEYWORDS,
    PEOPLE_KEYWORDS,
    TIME_KEYWORDS,
    SCENE_KEYWORDS,
)


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, round(value, 4)))


def calculate_template_similarity_score(text: str, corpus: list[str]) -> float:
    clean_text = (text or "").strip()
    peers = [item.strip() for item in corpus or [] if item and item.strip()]
    if not clean_text or not peers:
        return 0.0

    peer_counts = Counter(peers)
    if peer_counts[clean_text] > 1:
        return 1.0

    candidates = [peer for peer in peer_counts if peer != clean_text]
    if len(candidates) > 300:
        candidates = sorted(candidates, key=lambda peer: abs(len(peer) - len(clean_text)))[:300]
    similarities = [
        SequenceMatcher(None, clean_text, peer).ratio()
        for peer in candidates
    ]
    return _clamp(max(similarities, default=0.0))


def calculate_low_information_score(text: str) -> float:
    clean_text = (text or "").strip()
    if not clean_text:
        return 1.0
    if len(clean_text) < 6:
        return 1.0

    score = 0.0
    if _contains_any(clean_text, LOW_INFORMATION_KEYWORDS):
        score += 0.55
    if not _contains_any(clean_text, TENT_USAGE_KEYWORDS):
        score += 0.25
    if not _contains_any(clean_text, WEATHER_KEYWORDS + PEOPLE_KEYWORDS + TIME_KEYWORDS + SCENE_KEYWORDS):
        score += 0.15
    if len(clean_text) <= 12:
        score += 0.15
    return _clamp(score)


def calculate_over_positive_without_detail_score(text: str) -> float:
    clean_text = (text or "").strip()
    if not clean_text:
        return 0.0

    positive_hits = sum(1 for keyword in POSITIVE_GENERIC_KEYWORDS if keyword in clean_text)
    marketing_hits = sum(1 for keyword in REDBOOK_AD_KEYWORDS if keyword in clean_text)
    detail_hits = sum(
        1
        for keyword in TENT_USAGE_KEYWORDS + WEATHER_KEYWORDS + PEOPLE_KEYWORDS + TIME_KEYWORDS + SPECIFIC_PROBLEM_KEYWORDS
        if keyword in clean_text
    )
    if positive_hits == 0 and marketing_hits == 0:
        return 0.0
    base = min(0.75, positive_hits * 0.22 + marketing_hits * 0.12)
    if detail_hits == 0:
        base += 0.35
    elif detail_hits <= 1:
        base += 0.15
    else:
        base -= 0.2
    return _clamp(base)


def _calculate_text_template_score(text: str) -> float:
    clean_text = (text or "").strip()
    if not clean_text:
        return 1.0

    score = 0.0
    if calculate_low_information_score(clean_text) >= 0.7:
        score += 0.35
    if calculate_over_positive_without_detail_score(clean_text) >= 0.65:
        score += 0.35
    if len(set(clean_text)) <= max(4, len(clean_text) // 3):
        score += 0.15
    if "质量很好做工很好" in clean_text or clean_text.count("质量很好") >= 2:
        score += 0.35
    return _clamp(score)


def calculate_fake_review_risk_score(text: str, corpus: list[str] | None = None) -> float:
    template_score = _calculate_text_template_score(text)
    time_abnormal_score = 0.3
    low_information_score = calculate_low_information_score(text)
    over_positive_score = calculate_over_positive_without_detail_score(text)
    batch_similarity_score = calculate_template_similarity_score(text, corpus or [])

    risk_score = (
        0.30 * template_score
        + 0.25 * time_abnormal_score
        + 0.20 * low_information_score
        + 0.15 * over_positive_score
        + 0.10 * batch_similarity_score
    )
    return _clamp(risk_score)


def is_suspected_fake_review(text: str, corpus: list[str] | None = None) -> bool:
    return calculate_fake_review_risk_score(text, corpus) >= 0.65

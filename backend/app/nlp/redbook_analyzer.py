from app.nlp.keyword_dict import (
    POSITIVE_GENERIC_KEYWORDS,
    REDBOOK_AD_KEYWORDS,
    REDBOOK_REAL_EXPERIENCE_KEYWORDS,
    SCENE_KEYWORDS,
    SPECIFIC_PROBLEM_KEYWORDS,
    WEATHER_KEYWORDS,
)


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, round(value, 4)))


def is_suspected_ad_note(title: str, content: str) -> bool:
    text = f"{title or ''} {content or ''}"
    ad_hits = sum(1 for keyword in REDBOOK_AD_KEYWORDS if keyword in text)
    real_detail = _contains_any(text, REDBOOK_REAL_EXPERIENCE_KEYWORDS + WEATHER_KEYWORDS + SPECIFIC_PROBLEM_KEYWORDS)
    only_praise = _contains_any(text, POSITIVE_GENERIC_KEYWORDS) and not _contains_any(text, SPECIFIC_PROBLEM_KEYWORDS)
    return ad_hits >= 2 or (ad_hits >= 1 and not real_detail) or (only_praise and ad_hits >= 1)


def calculate_redbook_credibility_score(title: str, content: str, comments_text: str = "") -> float:
    text = f"{title or ''} {content or ''} {comments_text or ''}"
    score = 0.12
    feature_groups = [
        REDBOOK_REAL_EXPERIENCE_KEYWORDS,
        WEATHER_KEYWORDS,
        ["搭建", "收纳", "支架", "地钉"],
        SPECIFIC_PROBLEM_KEYWORDS,
        ["评论", "追问", "也说", "一致", "反馈"],
        ["避坑", "翻车", "缺点", "不足"],
        SCENE_KEYWORDS,
    ]
    for keywords in feature_groups:
        if _contains_any(text, keywords):
            score += 0.12
    if len(content or "") >= 40:
        score += 0.08
    if is_suspected_ad_note(title, content):
        score -= 0.25
    return _clamp(score)


def calculate_redbook_sentiment_score(title: str, content: str, comments_text: str = "") -> float:
    text = f"{title or ''} {content or ''} {comments_text or ''}"
    score = 62.0
    positive_hits = sum(1 for keyword in POSITIVE_GENERIC_KEYWORDS + ["好用", "稳", "方便", "舒服"] if keyword in text)
    risk_hits = sum(1 for keyword in SPECIFIC_PROBLEM_KEYWORDS + ["避坑", "翻车"] if keyword in text)
    score += min(18, positive_hits * 4)
    score -= min(45, risk_hits * 7)
    if is_suspected_ad_note(title, content):
        score -= 8
    return max(0.0, min(100.0, round(score, 2)))


def analyze_redbook_note(title, content, comments_text="") -> dict:
    text = f"{title or ''} {content or ''} {comments_text or ''}"
    risk_tags = sorted(set(keyword for keyword in SPECIFIC_PROBLEM_KEYWORDS if keyword in text))
    if "避坑" in text:
        risk_tags.append("避坑")
    if "翻车" in text:
        risk_tags.append("翻车")
    risk_tags = sorted(set(risk_tags))
    return {
        "is_suspected_ad": is_suspected_ad_note(title, content),
        "credibility_score": calculate_redbook_credibility_score(title, content, comments_text),
        "sentiment_score": calculate_redbook_sentiment_score(title, content, comments_text),
        "risk_tags": risk_tags,
    }


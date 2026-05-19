from app.nlp.keyword_dict import (
    CUSTOMER_SERVICE_KEYWORDS,
    LOW_RISK_NEGATIVE_KEYWORDS,
    REFUND_AMOUNT_KEYWORDS,
    REFUND_SPEED_KEYWORDS,
    RETURN_DIFFICULTY_KEYWORDS,
    SETUP_NEGATIVE_KEYWORDS,
    SHIPPING_FEE_DISPUTE_KEYWORDS,
    SMELL_NEGATIVE_KEYWORDS,
    SPACE_NEGATIVE_KEYWORDS,
    STORAGE_NEGATIVE_KEYWORDS,
    SUNPROOF_NEGATIVE_KEYWORDS,
    WATERPROOF_NEGATIVE_KEYWORDS,
    WINDPROOF_NEGATIVE_KEYWORDS,
)


DIMENSION_KEYWORDS = {
    "waterproof": WATERPROOF_NEGATIVE_KEYWORDS,
    "windproof": WINDPROOF_NEGATIVE_KEYWORDS,
    "space": SPACE_NEGATIVE_KEYWORDS,
    "storage": STORAGE_NEGATIVE_KEYWORDS,
    "setup": SETUP_NEGATIVE_KEYWORDS,
    "smell": SMELL_NEGATIVE_KEYWORDS,
    "sunproof": SUNPROOF_NEGATIVE_KEYWORDS,
    "return_after_sale": (
        RETURN_DIFFICULTY_KEYWORDS
        + REFUND_AMOUNT_KEYWORDS
        + REFUND_SPEED_KEYWORDS
        + SHIPPING_FEE_DISPUTE_KEYWORDS
        + CUSTOMER_SERVICE_KEYWORDS
    ),
}

HIGH_RISK_KEYWORDS = [
    "漏水",
    "全湿",
    "严重冷凝水",
    "杆子断",
    "支架断",
    "风一吹就倒",
    "结构倒塌",
    "质量问题不给退",
    "货不对板",
    "退款纠纷严重",
    "不给退",
    "退货被拒",
    "只退一部分",
]

MEDIUM_RISK_KEYWORDS = [
    "味道大",
    "熏人",
    "头疼",
    "不好收纳",
    "空间偏小",
    "空间虚标",
    "防晒差",
    "搭建困难",
    "难搭",
    "不好搭",
    "客服态度差",
    "客服不理人",
    "退款慢",
]


def _matched_keywords(text: str, keywords: list[str]) -> list[str]:
    return [keyword for keyword in keywords if keyword in text]


def classify_negative_review(text: str) -> dict:
    clean_text = text or ""
    affected_dimensions = [
        dimension for dimension, keywords in DIMENSION_KEYWORDS.items() if _matched_keywords(clean_text, keywords)
    ]
    low_risk_hits = _matched_keywords(clean_text, LOW_RISK_NEGATIVE_KEYWORDS)
    high_hits = _matched_keywords(clean_text, HIGH_RISK_KEYWORDS)
    medium_hits = _matched_keywords(clean_text, MEDIUM_RISK_KEYWORDS)

    risk_tags = []
    for dimension in affected_dimensions:
        risk_tags.extend(_matched_keywords(clean_text, DIMENSION_KEYWORDS[dimension]))
    risk_tags.extend(low_risk_hits)
    risk_tags = sorted(set(risk_tags))

    is_negative = bool(affected_dimensions or low_risk_hits or high_hits or medium_hits)
    if not is_negative:
        return {
            "is_negative": False,
            "negative_type": "none",
            "affected_dimensions": [],
            "risk_level": "none",
            "risk_tags": [],
        }

    if high_hits:
        risk_level = "high"
    elif medium_hits or affected_dimensions:
        risk_level = "medium"
    else:
        risk_level = "low"

    if "return_after_sale" in affected_dimensions:
        negative_type = "return_after_sale"
    elif "space" in affected_dimensions and ("虚标" in clean_text or "说是" in clean_text or "放不下" in clean_text):
        negative_type = "spec_mismatch"
    elif affected_dimensions:
        negative_type = "quality"
    else:
        negative_type = "logistics_or_preference"

    return {
        "is_negative": True,
        "negative_type": negative_type,
        "affected_dimensions": affected_dimensions,
        "risk_level": risk_level,
        "risk_tags": risk_tags,
    }


def is_valid_negative_review(text: str) -> bool:
    analysis = classify_negative_review(text)
    if not analysis["is_negative"]:
        return False
    return analysis["negative_type"] in {"quality", "spec_mismatch", "return_after_sale"} and bool(
        analysis["risk_tags"]
    )


from app.nlp.keyword_dict import (
    CUSTOMER_SERVICE_KEYWORDS,
    REFUND_AMOUNT_KEYWORDS,
    REFUND_SPEED_KEYWORDS,
    RETURN_DIFFICULTY_KEYWORDS,
    SHIPPING_FEE_DISPUTE_KEYWORDS,
)


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def analyze_return_review(text: str) -> dict:
    clean_text = text or ""
    result = {
        "return_difficulty": _contains_any(clean_text, RETURN_DIFFICULTY_KEYWORDS),
        "refund_amount_issue": _contains_any(clean_text, REFUND_AMOUNT_KEYWORDS),
        "refund_speed_issue": _contains_any(clean_text, REFUND_SPEED_KEYWORDS),
        "shipping_fee_dispute": _contains_any(clean_text, SHIPPING_FEE_DISPUTE_KEYWORDS),
        "bad_customer_service": _contains_any(clean_text, CUSTOMER_SERVICE_KEYWORDS),
        "risk_tags": [],
    }
    tag_map = {
        "return_difficulty": "退货困难",
        "refund_amount_issue": "退款金额争议",
        "refund_speed_issue": "退款速度慢",
        "shipping_fee_dispute": "退货运费争议",
        "bad_customer_service": "客服售后差",
    }
    result["risk_tags"] = [tag for key, tag in tag_map.items() if result[key]]
    return result


def calculate_return_negative_components(comments: list) -> dict:
    texts = [getattr(comment, "comment_text", comment) or "" for comment in comments]
    total = len(texts)
    if total == 0:
        return {
            "return_difficulty_rate": 0.0,
            "refund_amount_issue_rate": 0.0,
            "refund_speed_issue_rate": 0.0,
            "shipping_fee_dispute_rate": 0.0,
            "bad_customer_service_rate": 0.0,
        }

    analyses = [analyze_return_review(text) for text in texts]
    return {
        "return_difficulty_rate": round(sum(item["return_difficulty"] for item in analyses) / total, 4),
        "refund_amount_issue_rate": round(sum(item["refund_amount_issue"] for item in analyses) / total, 4),
        "refund_speed_issue_rate": round(sum(item["refund_speed_issue"] for item in analyses) / total, 4),
        "shipping_fee_dispute_rate": round(sum(item["shipping_fee_dispute"] for item in analyses) / total, 4),
        "bad_customer_service_rate": round(sum(item["bad_customer_service"] for item in analyses) / total, 4),
    }


import json
from collections import Counter, defaultdict


STANDARD_REVIEW_WEIGHTS = {
    "positive": 0.45,
    "neutral": 0.20,
    "negative": 0.35,
}

LAYER_PRIOR_RISK = {
    "positive": 0.04,
    "neutral": 0.10,
    "negative": 0.22,
}

RISK_DIMENSIONS = {
    "waterproof": {
        "keywords": ["漏水", "进水", "防水差", "雨天不行", "冷凝水", "渗水", "全湿", "leak", "waterproof"],
        "severity": 1.0,
    },
    "windproof": {
        "keywords": ["不防风", "风一吹", "杆子断", "支架断", "结构不稳", "塌", "broken_pole", "collapse"],
        "severity": 0.95,
    },
    "space": {
        "keywords": ["空间小", "空间虚标", "压抑", "太挤", "高度不够", "space_overclaim", "space"],
        "severity": 0.7,
    },
    "storage": {
        "keywords": ["不好收纳", "收不回去", "收纳袋", "折不回去", "hard_to_pack", "storage"],
        "severity": 0.55,
    },
    "setup": {
        "keywords": ["难搭", "不好搭", "说明书", "搭建复杂", "setup"],
        "severity": 0.55,
    },
    "smell_heat": {
        "keywords": ["味道大", "刺鼻", "熏人", "闷热", "太热", "不防晒", "防晒差", "smell", "sunproof"],
        "severity": 0.5,
    },
    "durability": {
        "keywords": ["质量问题", "开线", "破", "坏了", "耐用", "durability", "quality"],
        "severity": 0.75,
    },
    "return_after_sale": {
        "keywords": ["退货麻烦", "不给退", "退不了", "退款慢", "客服", "售后", "运费争议", "return", "refund"],
        "severity": 0.8,
    },
}


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(float(value), high))


def _parse_json_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
        if isinstance(value, list):
            return [str(item) for item in value]
        return [str(value)]
    except json.JSONDecodeError:
        return [item.strip() for item in str(raw).split(",") if item.strip()]


def classify_review_layer(comment) -> str:
    comment_type = str(getattr(comment, "comment_type", "") or "").lower()
    rating = getattr(comment, "rating", None)
    if "negative" in comment_type or "差" in comment_type:
        return "negative"
    if "neutral" in comment_type or "中" in comment_type:
        return "neutral"
    try:
        if rating is not None:
            rating_value = float(rating)
            if rating_value <= 2.5:
                return "negative"
            if rating_value < 4.5:
                return "neutral"
    except (TypeError, ValueError):
        pass
    return "positive"


def _text_for_comment(comment) -> str:
    parts = [str(getattr(comment, "comment_text", "") or "")]
    quality = getattr(comment, "quality_analysis", None)
    negative = getattr(comment, "negative_analysis", None)
    if quality:
        parts.extend(_parse_json_list(quality.risk_tags))
    if negative:
        parts.append(str(negative.negative_type or ""))
        parts.append(str(negative.risk_level or ""))
        parts.extend(_parse_json_list(negative.affected_dimension))
    return " ".join(part for part in parts if part).lower()


def matched_risk_dimensions(comment) -> dict[str, float]:
    haystack = _text_for_comment(comment)
    matched: dict[str, float] = {}
    for dimension, config in RISK_DIMENSIONS.items():
        if any(keyword.lower() in haystack for keyword in config["keywords"]):
            matched[dimension] = float(config["severity"])
    return matched


def _contains_usage_context(text: str) -> bool:
    keywords = [
        "露营",
        "帐篷",
        "下雨",
        "雨天",
        "风",
        "太阳",
        "一家",
        "孩子",
        "收纳",
        "搭建",
        "用了",
        "一晚",
        "周末",
        "camp",
        "rain",
        "wind",
    ]
    return any(keyword in text for keyword in keywords)


def evidence_weight(comment, risk_dimensions: dict[str, float] | None = None) -> float:
    risk_dimensions = risk_dimensions if risk_dimensions is not None else matched_risk_dimensions(comment)
    quality = getattr(comment, "quality_analysis", None)
    text = str(getattr(comment, "comment_text", "") or "")
    if quality:
        base = float(quality.effective_comment_weight or 0.0)
        if quality.is_low_information:
            base = min(base, 0.18)
        if quality.is_suspected_fake:
            base *= 0.35
    else:
        base = 0.25

    if getattr(comment, "has_image", False):
        base += 0.08
    if getattr(comment, "is_follow_up", False) or "追评" in text or "Follow-up:" in text:
        base += 0.14
    if _contains_usage_context(text):
        base += 0.10
    if risk_dimensions:
        base += 0.16
    if len(text.strip()) < 8 and not risk_dimensions:
        base *= 0.35
    return round(_clamp(base, 0.03, 1.0), 4)


def _bayesian_rate(risk_weight: float, total_weight: float, prior_rate: float, prior_weight: float = 8.0) -> float:
    return (risk_weight + prior_rate * prior_weight) / (total_weight + prior_weight)


def calculate_review_evidence(comments: list) -> dict:
    layer_counts: Counter[str] = Counter()
    layer_total_weight: defaultdict[str, float] = defaultdict(float)
    layer_risk_weight: defaultdict[str, float] = defaultdict(float)
    dimension_total_weight: defaultdict[str, float] = defaultdict(float)
    dimension_risk_weight: defaultdict[str, float] = defaultdict(float)
    warnings: list[str] = []

    for comment in comments:
        layer = classify_review_layer(comment)
        dimensions = matched_risk_dimensions(comment)
        weight = evidence_weight(comment, dimensions)
        layer_counts[layer] += 1
        layer_total_weight[layer] += weight
        if dimensions:
            layer_risk_weight[layer] += weight * max(dimensions.values())
        for dimension in RISK_DIMENSIONS:
            dimension_total_weight[dimension] += weight
        for dimension, severity in dimensions.items():
            dimension_risk_weight[dimension] += weight * severity

    total_count = sum(layer_counts.values())
    raw_distribution = {layer: layer_counts.get(layer, 0) for layer in STANDARD_REVIEW_WEIGHTS}
    raw_ratio = {
        layer: round(layer_counts.get(layer, 0) / total_count, 4) if total_count else 0.0
        for layer in STANDARD_REVIEW_WEIGHTS
    }
    sampling_bias_index = 0.5 * sum(
        abs(raw_ratio[layer] - STANDARD_REVIEW_WEIGHTS[layer]) for layer in STANDARD_REVIEW_WEIGHTS
    )

    normalized_layer_rates = {}
    standardized_risk_rate = 0.0
    for layer, standard_weight in STANDARD_REVIEW_WEIGHTS.items():
        rate = _bayesian_rate(layer_risk_weight[layer], layer_total_weight[layer], LAYER_PRIOR_RISK[layer])
        normalized_layer_rates[layer] = round(_clamp(rate), 4)
        standardized_risk_rate += standard_weight * rate

    dimension_risk_rates = {}
    for dimension in RISK_DIMENSIONS:
        dimension_risk_rates[dimension] = round(
            _clamp(_bayesian_rate(dimension_risk_weight[dimension], dimension_total_weight[dimension], 0.04, 6.0)),
            4,
        )

    missing_layers = [layer for layer, count in raw_distribution.items() if count == 0]
    small_layers = [layer for layer, count in raw_distribution.items() if 0 < count < 8]
    if missing_layers:
        warnings.append(f"missing review layers: {', '.join(missing_layers)}")
    if small_layers:
        warnings.append(f"thin review layers: {', '.join(small_layers)}")
    if sampling_bias_index > 0.35:
        warnings.append("raw positive/neutral/negative distribution differs materially from normalized scoring weights")

    sample_size_score = min(total_count / 120, 1.0)
    layer_coverage_score = 1 - len(missing_layers) / len(STANDARD_REVIEW_WEIGHTS)
    balance_score = 1 - min(sampling_bias_index, 0.7) / 0.7
    avg_effective_weight = (
        sum(layer_total_weight.values()) / total_count if total_count else 0.0
    )
    evidence_confidence = (
        0.35 * sample_size_score
        + 0.25 * layer_coverage_score
        + 0.20 * balance_score
        + 0.20 * min(avg_effective_weight / 0.55, 1.0)
    )

    standardized_risk_rate = _clamp(standardized_risk_rate)
    review_evidence_score = 100 - standardized_risk_rate * 100
    return {
        "raw_review_distribution": raw_distribution,
        "raw_review_ratio": raw_ratio,
        "normalized_review_weights": STANDARD_REVIEW_WEIGHTS.copy(),
        "normalized_layer_risk_rates": normalized_layer_rates,
        "standardized_risk_rate": round(standardized_risk_rate, 4),
        "dimension_risk_rates": dimension_risk_rates,
        "review_evidence_score": round(max(0.0, min(review_evidence_score, 100.0)), 2),
        "sampling_bias_index": round(sampling_bias_index, 4),
        "evidence_confidence_score": round(max(0.0, min(evidence_confidence * 100, 100.0)), 2),
        "review_sample_warnings": warnings,
    }


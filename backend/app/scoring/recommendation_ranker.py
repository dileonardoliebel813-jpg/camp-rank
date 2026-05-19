import json
import re

from sqlalchemy.orm import joinedload

from app.models import CanonicalProduct, Comment, Product
from app.scoring.explanation_generator import (
    generate_platform_explanation,
    generate_product_recommendation_reason,
    generate_risk_explanation,
)
from app.scoring.review_evidence_score import calculate_review_evidence
from app.services.spec_analysis_service import build_parameter_analysis, parameter_match_score
from app.utils.urls import public_product_url


def _parse_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
        if isinstance(value, list):
            return [str(item) for item in value]
        return [str(value)]
    except json.JSONDecodeError:
        return [item.strip() for item in raw.split(",") if item.strip()]


def filter_products_by_budget(
    products: list[dict],
    min_price: float | None,
    max_price: float | None,
) -> list[dict]:
    filtered = []
    for product in products:
        price = product.get("stable_final_price")
        if price is None:
            price = product.get("min_stable_final_price")
        if price is None:
            continue
        if min_price is not None and price < min_price:
            continue
        if max_price is not None and price > max_price:
            continue
        filtered.append(product)
    return filtered


SCENARIO_DIMENSION_WEIGHTS = {
    "newbie_weekend": {"setup": 0.22, "return_after_sale": 0.18, "smell_heat": 0.14, "storage": 0.10},
    "family_camping": {"space": 0.24, "durability": 0.16, "return_after_sale": 0.14, "setup": 0.10},
    "group_party": {"space": 0.30, "durability": 0.14, "setup": 0.10, "return_after_sale": 0.08},
    "overnight": {"waterproof": 0.28, "windproof": 0.20, "durability": 0.18, "smell_heat": 0.08},
    "rain_backup": {"waterproof": 0.34, "windproof": 0.18, "durability": 0.12, "return_after_sale": 0.08},
    "hiking_lightweight": {"storage": 0.28, "setup": 0.18, "smell_heat": 0.10, "durability": 0.08},
}


PREFERENCE_DIMENSION_WEIGHTS = {
    "balanced": {"return_after_sale": 0.12, "durability": 0.10},
    "lowest_price": {},
    "after_sale": {"return_after_sale": 0.34},
    "gift_package": {"space": 0.28},
    "portable": {"storage": 0.30, "setup": 0.14},
    "weather_protection": {"waterproof": 0.30, "windproof": 0.20, "durability": 0.10},
    "easy_setup": {"setup": 0.34, "storage": 0.10},
    "less_stuffy": {"smell_heat": 0.34},
}


SCENARIO_LABELS = {
    "newbie_weekend": "短途休闲露营",
    "family_camping": "家庭亲子露营",
    "group_party": "多人聚会/大空间需求",
    "overnight": "短途过夜露营",
    "rain_backup": "雨天/潮湿环境备用",
    "hiking_lightweight": "步行携带/收纳约束",
}


PREFERENCE_LABELS = {
    "balanced": "综合购买风险控制",
    "lowest_price": "价格敏感/到手价优先",
    "after_sale": "售后与退换保障",
    "gift_package": "容量与空间匹配",
    "portable": "收纳携带负担",
    "weather_protection": "防水/防风负面反馈",
    "easy_setup": "搭建复杂度敏感",
    "less_stuffy": "闷热/异味负面反馈",
}


def _parse_preferences(preference: str | list[str] | tuple[str, ...] | None) -> list[str]:
    if preference is None:
        return ["balanced"]
    if isinstance(preference, (list, tuple)):
        raw_values = preference
    else:
        raw_values = str(preference).split(",")
    values = []
    for raw in raw_values:
        value = str(raw).strip()
        if value and value not in values:
            values.append(value)
    if len(values) > 1 and "balanced" in values:
        values = [value for value in values if value != "balanced"]
    return values or ["balanced"]


def _preference_label(preferences: list[str]) -> str:
    return "、".join(PREFERENCE_LABELS.get(value, value) for value in preferences)


def _safe_float(value, fallback: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    return number


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(float(value), high))


def _confidence_adjusted_score(product: dict) -> float:
    final_score = _safe_float(product.get("final_score"))
    confidence = _safe_float(product.get("data_confidence_score"))
    if confidence < 30:
        return final_score - 15
    if confidence < 50:
        return final_score - 8
    return final_score


def _price_context(products: list[dict]) -> tuple[float | None, float | None]:
    prices = [
        _safe_float(product.get("stable_final_price"), -1)
        for product in products
        if product.get("stable_final_price") is not None
    ]
    prices = [price for price in prices if price >= 0]
    if not prices:
        return None, None
    return min(prices), max(prices)


def _price_score(product: dict, min_price: float | None, max_price: float | None) -> float:
    price = _safe_float(product.get("stable_final_price"), -1)
    if price < 0 or min_price is None or max_price is None:
        return _confidence_adjusted_score(product)
    if max_price <= min_price:
        return 85.0
    return round(_clamp(100 - ((price - min_price) / (max_price - min_price)) * 100), 2)


def _numeric_from_text(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"\d+(?:\.\d+)?", str(value))
    return float(match.group(0)) if match else None


def _dimension_quality(product: dict, dimension: str) -> float:
    rates = product.get("dimension_risk_rates") or {}
    if dimension not in rates:
        return _confidence_adjusted_score(product)
    # Dimension values are current comment-risk rates. Higher rate means more risk feedback.
    return round(_clamp(100 - _safe_float(rates.get(dimension)) * 220), 2)


def _overall_risk_quality(product: dict) -> float:
    rate = product.get("standardized_risk_rate")
    if rate is None:
        return _confidence_adjusted_score(product)
    return round(_clamp(100 - _safe_float(rate) * 160), 2)


def _capacity_score(product: dict, scenario: str, preferences: list[str]) -> float:
    capacity = str(product.get("capacity") or "")
    numbers = [int(value) for value in re.findall(r"\d+", capacity)]
    if not numbers:
        return 50.0
    max_people = max(numbers)
    if "portable" in preferences or scenario == "hiking_lightweight":
        if max_people <= 3:
            return 90.0
        if max_people <= 4:
            return 78.0
        if max_people <= 6:
            return 58.0
        return 45.0
    if scenario == "group_party" or "gift_package" in preferences:
        if max_people >= 8:
            return 100.0
        if max_people >= 6:
            return 72.0
        if max_people >= 5:
            return 60.0
        return 52.0
    if scenario == "family_camping":
        if max_people >= 6:
            return 90.0
        if max_people >= 4:
            return 76.0
        return 55.0
    return 65.0


def _max_capacity(product: dict) -> int:
    capacity = str(product.get("capacity") or "")
    numbers = [int(value) for value in re.findall(r"\d+", capacity)]
    return max(numbers) if numbers else 0


def _parameter_facts(product: dict) -> dict:
    analysis = product.get("parameter_analysis") or {}
    return analysis.get("facts") or {}


def _parameter_scores(product: dict) -> dict:
    analysis = product.get("parameter_analysis") or {}
    return analysis.get("scores") or {}


def _has_missing_parameter(product: dict, needle: str) -> bool:
    analysis = product.get("parameter_analysis") or {}
    decision = analysis.get("decision") or {}
    missing = decision.get("missing_parameters") or []
    return any(needle in str(item) for item in missing)


def _scenario_match_score(product: dict, scenario: str) -> float:
    use_case = str(product.get("use_case") or "")
    if use_case == scenario:
        return 100.0
    capacity = str(product.get("capacity") or "")
    numbers = [int(value) for value in re.findall(r"\d+", capacity)]
    max_people = max(numbers) if numbers else 0
    if scenario == "group_party" and max_people >= 8:
        return 95.0
    if scenario == "group_party" and use_case == "family_camping":
        return 82.0
    if scenario == "family_camping" and max_people >= 6:
        return 86.0
    if scenario in {"overnight", "rain_backup", "hiking_lightweight"}:
        return 55.0
    return 62.0


def _after_sale_text_score(product: dict) -> float:
    text = str(product.get("recommended_after_sale_service") or "")
    if not text:
        return 50.0
    score = 62.0
    if "免费上门退换" in text:
        score += 12
    if "闪电退款" in text or "极速审核" in text:
        score += 8
    if "京东发货&售后" in text or "京东售后" in text:
        score += 8
    if "假一赔四" in text:
        score += 4
    if "使用后不支持" in text:
        score -= 8
    if "7天无理由退货" in text:
        score += 5
    return round(_clamp(score), 2)


def _requirement_result(key: str, label: str, passed: bool, score: float, reason: str, required: bool = True) -> dict:
    return {
        "key": key,
        "label": label,
        "passed": bool(passed),
        "score": round(_clamp(score), 2),
        "reason": reason,
        "required": required,
    }


def _require_scenario(product: dict, scenario: str, preferences: list[str]) -> dict:
    label = SCENARIO_LABELS.get(scenario, scenario)
    score = _scenario_match_score(product, scenario)
    capacity = _max_capacity(product)
    facts = _parameter_facts(product)
    area = _numeric_from_text(facts.get("derived_floor_area_m2"))
    parameter_scores = _parameter_scores(product)
    space_score = _safe_float(parameter_scores.get("space"), 50)
    portability = _safe_float(parameter_scores.get("portability"), 50)

    if scenario == "group_party":
        passed = capacity >= 5 or (area is not None and area >= 5)
        reason = "容量或展开面积满足多人/大空间需求" if passed else "容量或展开面积不足以支撑多人/大空间需求"
    elif scenario == "family_camping":
        passed = capacity >= 4 or (area is not None and area >= 4)
        reason = "容量或展开面积满足家庭亲子场景" if passed else "容量或展开面积不够明确支撑家庭亲子场景"
    elif scenario == "hiking_lightweight":
        has_weight = bool(facts.get("weight_text"))
        has_volume = bool(facts.get("derived_packed_volume_l") or facts.get("packed_size_text"))
        passed = (has_weight or has_volume) and portability >= 62
        reason = "重量/收纳参数适合步行携带" if passed else "重量或收纳参数不足以确认轻便"
    elif scenario in {"overnight", "rain_backup"}:
        rates = product.get("dimension_risk_rates") or {}
        weather_risk = max(_safe_float(rates.get("waterproof")), _safe_float(rates.get("windproof")))
        has_weather_parameter = bool(facts.get("waterproof_index_outer") or facts.get("waterproof_index_floor") or facts.get("outer_material"))
        passed = weather_risk <= 0.06 and has_weather_parameter
        reason = "天气相关评论风险较低且有页面标称参数" if passed else "过夜/雨天场景的天气参数或评论风险仍需确认"
    else:
        passed = score >= 58
        reason = "场景基础匹配达标" if passed else "场景匹配偏弱"

    if "portable" in preferences and scenario != "hiking_lightweight":
        score = min(score, portability)
    if "gift_package" in preferences and scenario not in {"family_camping", "group_party"}:
        score = min(100, (score + space_score) / 2)
    return _requirement_result("scenario", f"使用场景：{label}", passed, score, reason)


def _require_lowest_price(product: dict, products: list[dict]) -> dict:
    min_price, max_price = _price_context(products)
    price = _safe_float(product.get("stable_final_price"), -1)
    if price < 0 or min_price is None or max_price is None:
        return _requirement_result("lowest_price", PREFERENCE_LABELS["lowest_price"], False, 0, "当前接口未返回可比较到手价")
    low_band = min_price + max((max_price - min_price) * 0.28, 35)
    passed = price <= low_band or price <= min_price * 1.18
    score = _price_score(product, min_price, max_price)
    reason = "到手价处于当前候选低价区间" if passed else "到手价不在当前候选低价区间"
    return _requirement_result("lowest_price", PREFERENCE_LABELS["lowest_price"], passed, score, reason)


def _require_after_sale(product: dict) -> dict:
    rates = product.get("dimension_risk_rates") or {}
    after_sale_risk = _safe_float(rates.get("return_after_sale"))
    text_score = _after_sale_text_score(product)
    passed = text_score >= 74 and after_sale_risk <= 0.09
    reason = "售后文本较明确且售后负面反馈不高" if passed else "售后文本或售后负面反馈未达到核心要求"
    score = text_score * 0.55 + _dimension_quality(product, "return_after_sale") * 0.45
    return _requirement_result("after_sale", PREFERENCE_LABELS["after_sale"], passed, score, reason)


def _require_space(product: dict, scenario: str) -> dict:
    facts = _parameter_facts(product)
    area = _numeric_from_text(facts.get("derived_floor_area_m2"))
    capacity = _max_capacity(product)
    score = max(_safe_float(_parameter_scores(product).get("space"), 50), _capacity_score(product, scenario, ["gift_package"]))
    if scenario == "group_party":
        passed = capacity >= 5 or (area is not None and area >= 5)
        reason = "容量/面积能支撑多人场景" if passed else "容量/面积不足以作为多人方案"
    else:
        passed = capacity >= 4 or (area is not None and area >= 4)
        reason = "容量/面积满足空间匹配要求" if passed else "容量或展开面积待确认/偏小"
    return _requirement_result("gift_package", PREFERENCE_LABELS["gift_package"], passed, score, reason)


def _require_portable(product: dict) -> dict:
    facts = _parameter_facts(product)
    weight = _numeric_from_text(facts.get("weight_text"))
    volume = _numeric_from_text(facts.get("derived_packed_volume_l"))
    has_weight = weight is not None
    has_volume = volume is not None or bool(facts.get("packed_size_text"))
    score = _safe_float(_parameter_scores(product).get("portability"), 50)
    passed = bool(has_weight or has_volume) and score >= 62 and (weight is None or weight <= 4.2) and (volume is None or volume <= 32)
    reason = "重量/收纳参数达到轻便要求" if passed else "重量或收纳体积缺失/偏高，不能按轻便款处理"
    return _requirement_result("portable", PREFERENCE_LABELS["portable"], passed, score, reason)


def _require_weather(product: dict) -> dict:
    rates = product.get("dimension_risk_rates") or {}
    waterproof_risk = _safe_float(rates.get("waterproof"))
    windproof_risk = _safe_float(rates.get("windproof"))
    facts = _parameter_facts(product)
    has_claim = bool(
        facts.get("waterproof_index_outer")
        or facts.get("waterproof_index_floor")
        or facts.get("outer_material")
        or facts.get("floor_material")
    )
    passed = waterproof_risk <= 0.055 and windproof_risk <= 0.055 and has_claim
    score = (
        _dimension_quality(product, "waterproof") * 0.45
        + _dimension_quality(product, "windproof") * 0.35
        + _safe_float(_parameter_scores(product).get("weather_claim"), 50) * 0.20
    )
    reason = "防水/防风负面反馈较低且有页面标称参数" if passed else "防水/防风反馈或页面参数仍需确认"
    return _requirement_result("weather_protection", PREFERENCE_LABELS["weather_protection"], passed, score, reason)


def _require_easy_setup(product: dict) -> dict:
    facts = _parameter_facts(product)
    setup_text = " ".join(str(value) for value in [facts.get("setup_type"), product.get("recommended_product_title"), product.get("product_name")] if value)
    setup_risk = _safe_float((product.get("dimension_risk_rates") or {}).get("setup"))
    has_easy_claim = any(keyword in setup_text for keyword in ("自动", "速开", "弹压", "免搭建", "快开", "弹簧"))
    passed = (has_easy_claim or setup_risk <= 0.01) and setup_risk <= 0.05
    score = max(_safe_float(_parameter_scores(product).get("setup"), 50), _dimension_quality(product, "setup"))
    reason = "搭建方式或评论反馈满足新手友好" if passed else "搭建方式不够明确或搭建负面反馈偏高"
    return _requirement_result("easy_setup", PREFERENCE_LABELS["easy_setup"], passed, score, reason)


def _require_less_stuffy(product: dict) -> dict:
    rate = _safe_float((product.get("dimension_risk_rates") or {}).get("smell_heat"))
    passed = rate <= 0.045
    score = _dimension_quality(product, "smell_heat")
    reason = "闷热/异味负面反馈较低" if passed else "闷热/异味负面反馈偏高"
    return _requirement_result("less_stuffy", PREFERENCE_LABELS["less_stuffy"], passed, score, reason)


def evaluate_selection_requirements(product: dict, products: list[dict], scenario: str, preferences: list[str]) -> list[dict]:
    requirements = [_require_scenario(product, scenario, preferences)]
    handlers = {
        "lowest_price": lambda: _require_lowest_price(product, products),
        "after_sale": lambda: _require_after_sale(product),
        "gift_package": lambda: _require_space(product, scenario),
        "portable": lambda: _require_portable(product),
        "weather_protection": lambda: _require_weather(product),
        "easy_setup": lambda: _require_easy_setup(product),
        "less_stuffy": lambda: _require_less_stuffy(product),
    }
    for preference in preferences:
        if preference == "balanced":
            continue
        handler = handlers.get(preference)
        if handler:
            requirements.append(handler())
    return requirements


def selection_tier_and_score(requirement_results: list[dict]) -> dict:
    required = [item for item in requirement_results if item.get("required", True)]
    matched = [item for item in required if item.get("passed")]
    unmet = [item for item in required if not item.get("passed")]
    ratio = len(matched) / len(required) if required else 1.0
    if not unmet:
        tier = "core_match"
    elif matched and ratio >= 0.5:
        tier = "partial_match"
    else:
        tier = "fallback"
    average_score = sum(_safe_float(item.get("score")) for item in required) / len(required) if required else 100.0
    strict_score = round(_clamp(average_score * (0.58 + ratio * 0.42)), 2)
    return {
        "selection_tier": tier,
        "strict_match_score": strict_score,
        "matched_requirements": [f"{item['label']}：{item['reason']}" for item in matched],
        "unmet_requirements": [f"{item['label']}：{item['reason']}" for item in unmet],
        "selection_summary": f"{len(matched)}/{len(required)} 项核心要求满足",
    }


def _combine_dimension_weights(scenario: str, preferences: list[str]) -> dict[str, float]:
    weights: dict[str, float] = {}
    sources = [SCENARIO_DIMENSION_WEIGHTS.get(scenario, SCENARIO_DIMENSION_WEIGHTS["newbie_weekend"])]
    sources.extend(PREFERENCE_DIMENSION_WEIGHTS.get(preference, {}) for preference in preferences)
    for source in sources:
        for key, value in source.items():
            weights[key] = weights.get(key, 0.0) + value
    return weights


def _weighted_dimension_score(product: dict, weights: dict[str, float]) -> float:
    if not weights:
        return _confidence_adjusted_score(product)
    total_weight = sum(weights.values())
    if total_weight <= 0:
        return _confidence_adjusted_score(product)
    return round(
        sum(_dimension_quality(product, dimension) * weight for dimension, weight in weights.items()) / total_weight,
        2,
    )


def _user_match_score(product: dict, products: list[dict], scenario: str, preference: str) -> tuple[float, list[str]]:
    preferences = _parse_preferences(preference)
    has_context_fields = any(
        product.get(key) is not None
        for key in (
            "stable_final_price",
            "standardized_risk_rate",
            "dimension_risk_rates",
            "capacity",
            "use_case",
            "parameter_match_score",
        )
    )
    base_score = _confidence_adjusted_score(product)
    if not has_context_fields:
        return round(base_score, 2), []

    min_price, max_price = _price_context(products)
    price = _price_score(product, min_price, max_price)
    risk = _overall_risk_quality(product)
    confidence = _safe_float(product.get("data_confidence_score"))
    dimension_weights = _combine_dimension_weights(scenario, preferences)
    dimension_score = _weighted_dimension_score(product, dimension_weights)
    capacity = _capacity_score(product, scenario, preferences)
    scenario_match = _scenario_match_score(product, scenario)
    after_sale = round((_dimension_quality(product, "return_after_sale") * 0.65) + (_after_sale_text_score(product) * 0.35), 2)
    parameter_match = _safe_float(product.get("parameter_match_score"), -1)

    weights = {
        "base": 0.28,
        "risk": 0.14,
        "confidence": 0.08,
        "dimension": 0.22,
        "scenario": 0.08,
        "price": 0.10,
        "capacity": 0.05,
        "after_sale": 0.05,
    }
    if parameter_match >= 0:
        weights["parameter"] = 0.12
        weights["base"] -= 0.04
        weights["dimension"] -= 0.04
        weights["scenario"] -= 0.02
        weights["capacity"] -= 0.02
    if "lowest_price" in preferences:
        price_only = len(preferences) == 1
        weights["price"] += 0.28 if price_only else 0.18
        weights["base"] -= 0.08 if price_only else 0.05
        weights["dimension"] -= 0.06 if price_only else 0.04
    if "after_sale" in preferences:
        weights["after_sale"] += 0.16
        weights["risk"] += 0.04
        weights["price"] -= 0.03
        weights["base"] -= 0.04
    if any(value in preferences for value in {"gift_package", "portable", "weather_protection", "easy_setup", "less_stuffy"}):
        weights["dimension"] += 0.08
        weights["base"] -= 0.04
    if "gift_package" in preferences:
        weights["capacity"] += 0.10
        weights["price"] -= 0.03
        weights["base"] -= 0.03
    if "portable" in preferences:
        weights["capacity"] += 0.04
        weights["dimension"] += 0.04
    if "weather_protection" in preferences:
        weights["risk"] += 0.04
        weights["dimension"] += 0.05
        weights["price"] -= 0.03
    if "easy_setup" in preferences or "less_stuffy" in preferences:
        weights["dimension"] += 0.04
    if scenario in {"group_party", "family_camping"}:
        weights["capacity"] += 0.12 if scenario == "group_party" else 0.07
        weights["dimension"] += 0.05
        weights["price"] -= 0.03 if scenario == "group_party" else 0.01
        weights["base"] -= 0.08 if scenario == "group_party" else 0.05
    if scenario in {"overnight", "rain_backup"}:
        weights["dimension"] += 0.08
        weights["risk"] += 0.04
        weights["price"] -= 0.04
        weights["base"] -= 0.04

    total_weight = sum(weights.values())
    score = (
        base_score * weights["base"]
        + risk * weights["risk"]
        + confidence * weights["confidence"]
        + dimension_score * weights["dimension"]
        + scenario_match * weights["scenario"]
        + price * weights["price"]
        + capacity * weights["capacity"]
        + after_sale * weights["after_sale"]
        + (parameter_match * weights.get("parameter", 0.0))
    ) / total_weight

    factors = [
        f"本次场景：{SCENARIO_LABELS.get(scenario, scenario)}",
        f"本次偏好：{_preference_label(preferences)}",
        f"到手价相对得分 {round(price, 1)}",
        f"校正后风险相对得分 {round(risk, 1)}",
        f"场景相关评论维度得分 {round(dimension_score, 1)}",
    ]
    if any(value in preferences for value in {"gift_package", "portable"}) or scenario in {"family_camping", "group_party", "hiking_lightweight"}:
        factors.append(f"容量标签匹配得分 {round(capacity, 1)}")
    if "after_sale" in preferences:
        factors.append(f"售后文本和售后反馈得分 {round(after_sale, 1)}")
    if parameter_match >= 0:
        factors.append(f"商品参数匹配得分 {round(parameter_match, 1)}")

    return round(_clamp(score), 2), factors


def rank_products(products: list[dict], scenario: str = "newbie_weekend", preference: str = "balanced") -> list[dict]:
    enriched = []
    preferences = _parse_preferences(preference)
    for product in products:
        item = dict(product)
        user_score, factors = _user_match_score(item, products, scenario, preference)
        requirement_results = evaluate_selection_requirements(item, products, scenario, preferences)
        selection = selection_tier_and_score(requirement_results)
        item["user_match_score"] = user_score
        item["ranking_factors"] = factors
        item["active_scenario"] = scenario
        item["active_preference"] = ",".join(preferences)
        item["selection_requirements"] = requirement_results
        item.update(selection)
        enriched.append(item)

    tier_rank = {"core_match": 2, "partial_match": 1, "fallback": 0}

    def key(product: dict) -> tuple[int, float, float, float, float, float]:
        tier = tier_rank.get(product.get("selection_tier"), 0)
        strict_score = _safe_float(product.get("strict_match_score"))
        user_score = _safe_float(product.get("user_match_score"))
        final_score = float(product.get("final_score") or 0)
        confidence = float(product.get("data_confidence_score") or 0)
        price = _safe_float(product.get("stable_final_price"), 10**9)
        return (tier, strict_score, user_score, confidence, final_score, -price)

    return sorted(enriched, key=key, reverse=True)


def _offer_dict(product: Product) -> dict:
    price = product.prices[-1] if product.prices else None
    analysis = product.platform_offer_analysis
    return_policy = product.return_policy
    benefit = product.benefit
    raw_specs = {}
    if product.spec and product.spec.raw_specs_json:
        try:
            raw_specs = json.loads(product.spec.raw_specs_json)
        except json.JSONDecodeError:
            raw_specs = {}
    parameter_analysis = build_parameter_analysis(product.spec)
    return {
        "platform": product.platform,
        "platform_product_id": product.platform_product_id,
        "title": product.title,
        "shop_name": product.shop_name,
        "product_url": public_product_url(product.product_url),
        "stable_final_price": price.stable_final_price if price else 0.0,
        "theoretical_lowest_price": price.theoretical_lowest_price if price else 0.0,
        "coupon_reliability_score": price.coupon_reliability_score if price else 0.0,
        "gift_estimated_value": benefit.gift_estimated_value if benefit else 0.0,
        "gift_adjusted_cost": analysis.gift_adjusted_cost if analysis else 0.0,
        "return_protection_score": return_policy.return_protection_score if return_policy else 0.0,
        "return_risk_score": return_policy.return_risk_score if return_policy else 0.0,
        "return_risk_cost": return_policy.return_risk_cost if return_policy else 0.0,
        "return_condition_text": return_policy.return_condition_text if return_policy else "",
        "risk_adjusted_cost": analysis.risk_adjusted_cost if analysis else 0.0,
        "platform_buy_score": analysis.platform_buy_score if analysis else 0.0,
        "is_lowest_price": bool(analysis and analysis.is_lowest_price),
        "is_recommended_platform": bool(analysis and analysis.is_recommended_platform),
        "warning_tags": _parse_tags(analysis.warning_tags if analysis else None),
        "data_confidence_score": product.canonical_product.data_confidence_score if product.canonical_product else 0.0,
        "source_sku_titles": raw_specs.get("top_sku_titles", []) if isinstance(raw_specs, dict) else [],
        "parameter_analysis": parameter_analysis,
    }


def _advantages_from_score(score) -> list[str]:
    if not score:
        return ["sample data keeps a comparable platform structure"]
    dimensions = [
        ("waterproof performance", score.waterproof_score),
        ("windproof stability", score.windproof_score),
        ("usable space", score.space_score),
        ("easy setup", score.setup_score),
        ("return and after-sale support", score.return_after_sale_score),
        ("platform benefits", score.platform_benefit_score),
    ]
    return [name for name, value in sorted(dimensions, key=lambda item: item[1], reverse=True)[:3]]


def _recommend_level(final_score: float) -> str:
    if final_score >= 82:
        return "strong_recommend"
    if final_score >= 70:
        return "recommend"
    if final_score >= 60:
        return "cautious"
    return "not_recommended"


def build_recommendations(
    db,
    min_price=None,
    max_price=None,
    scenario="newbie_weekend",
    preference="balanced",
    limit=10,
) -> list[dict]:
    canonicals = (
        db.query(CanonicalProduct)
        .options(
            joinedload(CanonicalProduct.product_score),
            joinedload(CanonicalProduct.products).joinedload(Product.prices),
            joinedload(CanonicalProduct.products).joinedload(Product.spec),
            joinedload(CanonicalProduct.products).joinedload(Product.benefit),
            joinedload(CanonicalProduct.products).joinedload(Product.return_policy),
            joinedload(CanonicalProduct.products).joinedload(Product.platform_offer_analysis),
            joinedload(CanonicalProduct.products).joinedload(Product.comments).joinedload(Comment.quality_analysis),
            joinedload(CanonicalProduct.products).joinedload(Product.comments).joinedload(Comment.negative_analysis),
            joinedload(CanonicalProduct.redbook_notes),
        )
        .all()
    )

    results = []
    for canonical in canonicals:
        if not canonical.products:
            continue
        offers = [_offer_dict(product) for product in canonical.products if product.prices]
        if not offers:
            continue
        lowest = next((offer for offer in offers if offer["is_lowest_price"]), min(offers, key=lambda item: item["stable_final_price"]))
        recommended = next(
            (offer for offer in offers if offer["is_recommended_platform"]),
            max(offers, key=lambda item: item["platform_buy_score"]),
        )
        score = canonical.product_score
        final_score = score.final_score if score else 0.0
        data_confidence = score.data_confidence_score if score else canonical.data_confidence_score
        risk_tags = sorted(set(recommended["warning_tags"] + [tag for offer in offers for tag in offer["warning_tags"]]))
        risks = generate_risk_explanation(risk_tags)
        advantages = _advantages_from_score(score)
        comments = [comment for product in canonical.products for comment in product.comments]
        review_evidence = calculate_review_evidence(comments)
        parameter_analysis = recommended.get("parameter_analysis") or build_parameter_analysis(None)
        parameter_match = parameter_match_score(parameter_analysis, scenario, _parse_preferences(preference))
        summary = {
            "canonical_product_id": canonical.id,
            "product_name": canonical.normalized_name,
            "brand": canonical.brand,
            "model_name": canonical.model_name,
            "capacity": canonical.capacity,
            "use_case": canonical.use_case,
            "final_score": round(final_score, 2),
            "data_confidence_score": round(data_confidence, 2),
            "recommended_platform": recommended["platform"],
            "recommended_platform_product_id": recommended["platform_product_id"],
            "recommended_product_title": recommended["title"],
            "recommended_product_url": recommended["product_url"],
            "recommended_shop_name": recommended["shop_name"],
            "recommended_after_sale_service": recommended["return_condition_text"],
            "source_sku_titles": recommended["source_sku_titles"][:5],
            "parameter_analysis": parameter_analysis,
            "parameter_score": (parameter_analysis.get("scores") or {}).get("overall"),
            "parameter_match_score": parameter_match,
            "parameter_summary": parameter_analysis.get("summary", []),
            "parameter_highlights": parameter_analysis.get("highlights", []),
            "parameter_cautions": parameter_analysis.get("cautions", []),
            "lowest_price_platform": lowest["platform"],
            "lowest_price_product_id": lowest["platform_product_id"],
            "lowest_price_product_url": lowest["product_url"],
            "stable_final_price": recommended["stable_final_price"],
            "theoretical_lowest_price": recommended["theoretical_lowest_price"],
            "price_gap": round(recommended["stable_final_price"] - lowest["stable_final_price"], 2),
            "risk_adjusted_cost": recommended["risk_adjusted_cost"],
            "advantages": advantages,
            "risks": risks,
            "risk_tags": risk_tags,
            "recommend_level": _recommend_level(final_score),
            "platform_explanation": generate_platform_explanation(lowest, recommended),
            "comment_count": len(comments),
            "review_evidence_score": review_evidence["review_evidence_score"],
            "evidence_confidence_score": review_evidence["evidence_confidence_score"],
            "sampling_bias_index": review_evidence["sampling_bias_index"],
            "standardized_risk_rate": review_evidence["standardized_risk_rate"],
            "raw_review_distribution": review_evidence["raw_review_distribution"],
            "dimension_risk_rates": review_evidence["dimension_risk_rates"],
            "review_sample_warnings": review_evidence["review_sample_warnings"],
            "platform_product_ids": [product.platform_product_id for product in canonical.products],
        }
        summary["reason"] = generate_product_recommendation_reason(summary)
        results.append(summary)

    results = filter_products_by_budget(results, min_price, max_price)
    return rank_products(results, scenario, preference)[: int(limit or 10)]

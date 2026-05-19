from __future__ import annotations

from collections import Counter
from typing import Any


PRICE_FIELDS = ("current_price",)
SPEC_FIELDS = ("waterproof_index_outer", "waterproof_index_floor", "weight", "expanded_size", "pole_material")
BENEFIT_FIELDS = ("free_shipping", "shipping_insurance", "return_7_days", "fast_refund", "price_protection", "self_operated")
RETURN_POLICY_FIELDS = (
    "return_shipping_insurance",
    "return_shipping_payer",
    "return_condition_text",
    "opened_return_allowed",
    "quality_issue_free_return",
    "refund_speed_type",
    "refund_full_amount",
)
COMMENT_FIELDS = ("comment_text", "rating", "comment_time")
REDBOOK_FIELDS = ("title", "content", "comments_text")
FIELD_ALIASES = {
    "weight": ("weight", "weight_kg"),
    "expanded_size": ("expanded_size", "expanded_length_cm", "floor_area_m2"),
    "current_price": ("current_price", "price", "deal_price", "zk_final_price", "min_group_price"),
    "comment_text": ("comment_text", "content", "text"),
}


def _is_present(value: Any) -> bool:
    if value is None or value == "":
        return False
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def _has_field(source: dict[str, Any], field: str) -> bool:
    return any(_is_present(source.get(alias)) for alias in FIELD_ALIASES.get(field, (field,)))


def _score(record: dict[str, Any], fields: tuple[str, ...], nested_key: str | None = None) -> tuple[float, list[str]]:
    source = record.get(nested_key) if nested_key else record
    if isinstance(source, list):
        if not source:
            return 0.0, [nested_key or "items"]
        nested_scores = [_score(item, fields) for item in source if isinstance(item, dict)]
        if not nested_scores:
            return 0.0, [nested_key or "items"]
        avg = sum(item_score for item_score, _ in nested_scores) / len(nested_scores)
        missing = sorted({field for _, missing_fields in nested_scores for field in missing_fields})
        return round(avg, 4), missing
    if not isinstance(source, dict):
        source = {}
    missing = [field for field in fields if not _has_field(source, field)]
    return round((len(fields) - len(missing)) / len(fields), 4), missing


def calculate_platform_record_completeness(record: dict, platform: str) -> dict:
    is_jd_only = str(platform or "").upper() == "JD"
    price_score, price_missing = _score(record, PRICE_FIELDS, "price" if isinstance(record.get("price"), dict) else None)
    spec_source = "specs" if isinstance(record.get("specs"), dict) else None
    spec_score, spec_missing = _score(record, SPEC_FIELDS, spec_source)
    benefit_source = "benefit" if isinstance(record.get("benefit"), dict) else None
    benefit_score, benefit_missing = _score(record, BENEFIT_FIELDS, benefit_source)
    return_source = "return_policy" if isinstance(record.get("return_policy"), dict) else None
    return_score, return_missing = _score(record, RETURN_POLICY_FIELDS, return_source)

    comment_score, comment_missing = _score(record, COMMENT_FIELDS, "comments")
    if is_jd_only:
        redbook_score, redbook_missing = 1.0, []
    else:
        redbook_score, redbook_missing = _score(record, REDBOOK_FIELDS, "redbook_notes")

    scores = {
        "price_completeness": price_score,
        "spec_completeness": spec_score,
        "benefit_completeness": benefit_score,
        "return_policy_completeness": return_score,
        "comment_completeness": comment_score,
        "redbook_completeness": redbook_score,
    }
    missing_fields = {
        "price": price_missing,
        "spec": spec_missing,
        "benefit": benefit_missing,
        "return_policy": return_missing,
        "comment": comment_missing,
    }
    if not is_jd_only:
        missing_fields["redbook"] = redbook_missing
    scores["overall_completeness"] = round(sum(scores.values()) / len(scores), 4)
    scores["platform"] = platform.upper()
    scores["missing_fields"] = missing_fields
    return scores


def summarize_import_quality(records: list[dict], platform: str) -> dict:
    if not records:
        empty = calculate_platform_record_completeness({}, platform)
        return {
            "platform": platform.upper(),
            "record_count": 0,
            **{key: 0.0 for key in empty if key.endswith("_completeness")},
            "overall_completeness": 0.0,
            "missing_fields": empty["missing_fields"],
        }

    results = [calculate_platform_record_completeness(record, platform) for record in records]
    summary = {"platform": platform.upper(), "record_count": len(records)}
    for key in (
        "price_completeness",
        "spec_completeness",
        "benefit_completeness",
        "return_policy_completeness",
        "comment_completeness",
        "redbook_completeness",
        "overall_completeness",
    ):
        summary[key] = round(sum(result[key] for result in results) / len(results), 4)

    missing_counter: dict[str, Counter] = {
        "price": Counter(),
        "spec": Counter(),
        "benefit": Counter(),
        "return_policy": Counter(),
        "comment": Counter(),
        "redbook": Counter(),
    }
    for result in results:
        for group, fields in result["missing_fields"].items():
            missing_counter[group].update(fields)
    summary["missing_fields"] = {
        group: dict(counter) for group, counter in missing_counter.items() if counter
    }
    return summary


def generate_data_confidence_warning(completeness_summary: dict) -> list[str]:
    warnings: list[str] = []
    if completeness_summary.get("return_policy_completeness", 0) < 0.8:
        warnings.append("缺少退货字段，退货评分置信度降低")
    if completeness_summary.get("comment_completeness", 0) < 0.8:
        warnings.append("缺少评论数据，评论风险判断置信度降低")
    if completeness_summary.get("spec_completeness", 0) < 0.8:
        warnings.append("缺少商品参数，产品能力评分置信度降低")
    if completeness_summary.get("benefit_completeness", 0) < 0.8:
        warnings.append("缺少优惠/平台权益字段，平台购买评分置信度降低")
    if completeness_summary.get("platform") != "JD" and completeness_summary.get("redbook_completeness", 0) < 0.8:
        warnings.append("缺少小红书口碑样本，外部口碑修正置信度降低")
    if completeness_summary.get("price_completeness", 0) < 1.0:
        warnings.append("缺少价格字段，价格比较置信度降低")
    return warnings


def build_quality_records_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    products = {str(item.get("platform_product_id")): dict(item) for item in payload.get("platform_products", [])}
    for price in payload.get("product_prices", []):
        products.setdefault(str(price.get("platform_product_id")), {})["price"] = price
        products[str(price.get("platform_product_id"))].update(price)
    for spec in payload.get("product_specs", []):
        products.setdefault(str(spec.get("platform_product_id")), {})["specs"] = spec
    for benefit in payload.get("product_benefits", []):
        products.setdefault(str(benefit.get("platform_product_id")), {})["benefit"] = benefit
    for policy in payload.get("return_policies", []):
        products.setdefault(str(policy.get("platform_product_id")), {})["return_policy"] = policy
    for comment in payload.get("comments", []):
        products.setdefault(str(comment.get("platform_product_id")), {}).setdefault("comments", []).append(comment)
    redbook_notes = payload.get("redbook_notes", [])
    for product in products.values():
        product["redbook_notes"] = redbook_notes
    return list(products.values())

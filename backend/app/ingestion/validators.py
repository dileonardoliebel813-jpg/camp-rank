def _is_missing(value) -> bool:
    return value is None or value == ""


def validate_required_product_fields(data) -> list[str]:
    missing = []
    for field in ("title", "platform", "platform_product_id", "price"):
        if _is_missing(data.get(field)):
            missing.append(f"missing required product field: {field}")
    return missing


def validate_price_fields(data) -> list[str]:
    warnings = []
    for field in (
        "original_price",
        "current_price",
        "stable_final_price",
        "theoretical_lowest_price",
        "shipping_fee",
    ):
        value = data.get(field)
        if value is not None and float(value) < 0:
            warnings.append(f"{field} cannot be negative")
    current_price = data.get("current_price")
    theoretical = data.get("theoretical_lowest_price")
    stable = data.get("stable_final_price")
    if current_price is not None and theoretical is not None and float(theoretical) > float(current_price) * 1.25:
        warnings.append("theoretical_lowest_price is much higher than current_price")
    if stable is not None and float(stable) < 0:
        warnings.append("stable_final_price cannot be below 0")
    return warnings


def validate_spec_fields(data) -> list[str]:
    warnings = []
    weight = data.get("weight_kg")
    if weight is not None and not 0.5 <= float(weight) <= 30:
        warnings.append("weight_kg out of reasonable range: 0.5-30kg")
    for field in ("waterproof_index_outer", "waterproof_index_floor", "waterproof_index"):
        value = data.get(field)
        if value is not None and not 0 <= float(value) <= 10000:
            warnings.append(f"{field} out of reasonable range: 0-10000mm")
    floor_area = data.get("floor_area_m2")
    if floor_area is not None and not 0.5 <= float(floor_area) <= 30:
        warnings.append("floor_area_m2 out of reasonable range: 0.5-30m2")
    return warnings


def generate_data_quality_warnings(data) -> list[str]:
    warnings = []
    if not data.get("waterproof_index_outer") and not data.get("waterproof_index_floor"):
        warnings.append("missing waterproof parameters")
    if not data.get("weight_kg") and not data.get("weight"):
        warnings.append("missing weight")
    return_fields = [
        "return_shipping_insurance",
        "return_shipping_payer",
        "opened_return_allowed",
        "quality_issue_free_return",
        "refund_speed_type",
        "refund_full_amount",
    ]
    if any(field in data for field in return_fields) and any(_is_missing(data.get(field)) for field in return_fields):
        warnings.append("missing return policy fields")
    comment_count = data.get("comment_count")
    if comment_count is not None and int(comment_count or 0) < 3:
        warnings.append("insufficient comments")
    price_fields = ("original_price", "current_price", "shop_coupon_amount", "platform_coupon_amount")
    if any(field in data for field in price_fields) and any(_is_missing(data.get(field)) for field in price_fields[:2]):
        warnings.append("incomplete price fields")
    if data.get("redbook_note_count") == 0 or data.get("redbook_missing"):
        warnings.append("missing redbook samples")
    return warnings


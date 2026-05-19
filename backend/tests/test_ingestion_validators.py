from app.ingestion.validators import (
    generate_data_quality_warnings,
    validate_price_fields,
    validate_required_product_fields,
    validate_spec_fields,
)


def test_missing_required_product_fields_warns():
    warnings = validate_required_product_fields({"platform": "JD"})
    assert "missing required product field: title" in warnings
    assert "missing required product field: platform_product_id" in warnings
    assert "missing required product field: price" in warnings


def test_negative_price_warns():
    warnings = validate_price_fields({"current_price": -1, "stable_final_price": 10})
    assert "current_price cannot be negative" in warnings


def test_unreasonable_weight_warns():
    warnings = validate_spec_fields({"weight_kg": 50, "waterproof_index_outer": 2000, "floor_area_m2": 3})
    assert any("weight_kg out of reasonable range" in warning for warning in warnings)


def test_missing_waterproof_quality_warning():
    warnings = generate_data_quality_warnings({"weight_kg": 2.1, "comment_count": 2, "redbook_missing": True})
    assert "missing waterproof parameters" in warnings
    assert "insufficient comments" in warnings
    assert "missing redbook samples" in warnings


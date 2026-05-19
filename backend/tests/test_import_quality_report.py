from app.ingestion.data_quality import (
    calculate_platform_record_completeness,
    generate_data_confidence_warning,
    summarize_import_quality,
)


FULL_RECORD = {
    "current_price": "699",
    "specs": {
        "waterproof_index_outer": "2000",
        "waterproof_index_floor": "4000",
        "weight": "1.8kg",
        "expanded_size": "210*125*100cm",
        "pole_material": "aluminum",
    },
    "benefit": {
        "free_shipping": True,
        "shipping_insurance": True,
        "return_7_days": True,
        "fast_refund": True,
        "price_protection": True,
        "self_operated": True,
    },
    "return_policy": {
        "return_shipping_insurance": True,
        "return_shipping_payer": "seller",
        "return_condition_text": "7 days",
        "opened_return_allowed": True,
        "quality_issue_free_return": True,
        "refund_speed_type": "fast_refund",
        "refund_full_amount": True,
    },
    "comments": [{"comment_text": "Used in rain", "rating": 5, "comment_time": "2026-04-01"}],
    "redbook_notes": [{"title": "note", "content": "field use", "comments_text": "question"}],
}


def test_field_completeness_calculation_full_record():
    result = calculate_platform_record_completeness(FULL_RECORD, "JD")
    assert result["price_completeness"] == 1.0
    assert result["return_policy_completeness"] == 1.0
    assert result["overall_completeness"] == 1.0


def test_missing_return_fields_generate_warning():
    summary = summarize_import_quality([{**FULL_RECORD, "return_policy": {}}], "JD")
    warnings = generate_data_confidence_warning(summary)
    assert any("退货字段" in warning for warning in warnings)


def test_missing_comments_lowers_comment_completeness():
    result = calculate_platform_record_completeness({**FULL_RECORD, "comments": []}, "JD")
    assert result["comment_completeness"] == 0.0


def test_jd_only_quality_does_not_require_redbook():
    record = {key: value for key, value in FULL_RECORD.items() if key != "redbook_notes"}
    result = calculate_platform_record_completeness(record, "JD")
    warnings = generate_data_confidence_warning(result)
    assert result["redbook_completeness"] == 1.0
    assert "redbook" not in result["missing_fields"]
    assert not any("小红书" in warning for warning in warnings)


def test_overall_completeness_higher_when_fields_complete():
    full = calculate_platform_record_completeness(FULL_RECORD, "JD")
    partial = calculate_platform_record_completeness({"current_price": "699"}, "JD")
    assert full["overall_completeness"] > partial["overall_completeness"]

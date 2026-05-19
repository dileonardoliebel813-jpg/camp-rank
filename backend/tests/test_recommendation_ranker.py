from app.scoring.recommendation_ranker import (
    build_recommendations,
    evaluate_selection_requirements,
    filter_products_by_budget,
    rank_products,
    selection_tier_and_score,
)
from app.services.scoring_service import calculate_all_scores


def test_budget_filter_uses_recommended_or_lowest_price():
    products = [
        {"product_name": "A", "stable_final_price": 300},
        {"product_name": "B", "stable_final_price": 600},
        {"product_name": "C", "min_stable_final_price": 450},
    ]
    result = filter_products_by_budget(products, 350, 500)
    assert [item["product_name"] for item in result] == ["C"]


def test_topn_sorting_considers_score_and_confidence():
    products = [
        {"product_name": "low confidence", "final_score": 95, "data_confidence_score": 25},
        {"product_name": "solid", "final_score": 88, "data_confidence_score": 80},
        {"product_name": "ok", "final_score": 70, "data_confidence_score": 90},
    ]
    ranked = rank_products(products)
    assert ranked[0]["product_name"] == "solid"


def test_build_recommendations_returns_required_fields(db_session):
    calculate_all_scores(db_session)
    result = build_recommendations(db_session, limit=3)
    required = {
        "canonical_product_id",
        "product_name",
        "brand",
        "model_name",
        "final_score",
        "data_confidence_score",
        "recommended_platform",
        "lowest_price_platform",
        "recommended_after_sale_service",
        "stable_final_price",
        "theoretical_lowest_price",
        "price_gap",
        "risk_adjusted_cost",
        "reason",
        "advantages",
        "risks",
        "risk_tags",
    }
    assert len(result) == 3
    assert required.issubset(result[0].keys())


def test_low_confidence_product_is_not_forced_to_first():
    products = [
        {"product_name": "thin data", "final_score": 90, "data_confidence_score": 20},
        {"product_name": "better evidence", "final_score": 82, "data_confidence_score": 85},
    ]
    assert rank_products(products)[0]["product_name"] == "better evidence"


def test_lowest_price_preference_can_change_top_recommendation():
    products = [
        {
            "product_name": "higher base score",
            "final_score": 88,
            "data_confidence_score": 82,
            "stable_final_price": 220,
            "standardized_risk_rate": 0.08,
            "dimension_risk_rates": {"setup": 0.02, "return_after_sale": 0.02},
            "capacity": "3-4人",
            "use_case": "newbie_weekend",
        },
        {
            "product_name": "lower price",
            "final_score": 80,
            "data_confidence_score": 82,
            "stable_final_price": 120,
            "standardized_risk_rate": 0.1,
            "dimension_risk_rates": {"setup": 0.03, "return_after_sale": 0.03},
            "capacity": "3-4人",
            "use_case": "newbie_weekend",
        },
    ]

    ranked = rank_products(products, scenario="newbie_weekend", preference="lowest_price")

    assert ranked[0]["product_name"] == "lower price"
    assert ranked[0]["user_match_score"] != ranked[0]["final_score"]
    assert ranked[0]["ranking_factors"]


def test_after_sale_preference_uses_return_feedback_and_policy_text():
    products = [
        {
            "product_name": "better after sale",
            "final_score": 80,
            "data_confidence_score": 82,
            "stable_final_price": 170,
            "standardized_risk_rate": 0.12,
            "dimension_risk_rates": {"return_after_sale": 0.01, "setup": 0.04},
            "recommended_after_sale_service": "免费上门退换 闪电退款 京东发货&售后 支持7天无理由退货",
            "capacity": "3-4人",
            "use_case": "newbie_weekend",
        },
        {
            "product_name": "higher base score worse after sale",
            "final_score": 88,
            "data_confidence_score": 82,
            "stable_final_price": 160,
            "standardized_risk_rate": 0.12,
            "dimension_risk_rates": {"return_after_sale": 0.22, "setup": 0.02},
            "recommended_after_sale_service": "支持7天无理由退货(使用后不支持)",
            "capacity": "3-4人",
            "use_case": "newbie_weekend",
        },
    ]

    ranked = rank_products(products, scenario="newbie_weekend", preference="after_sale")

    assert ranked[0]["product_name"] == "better after sale"


def test_weather_preference_uses_waterproof_and_windproof_feedback():
    products = [
        {
            "product_name": "weather safer sample",
            "final_score": 80,
            "data_confidence_score": 82,
            "stable_final_price": 180,
            "standardized_risk_rate": 0.14,
            "dimension_risk_rates": {"waterproof": 0.01, "windproof": 0.01, "durability": 0.02},
            "capacity": "3-4人",
            "use_case": "family_camping",
        },
        {
            "product_name": "higher base score weather risk",
            "final_score": 88,
            "data_confidence_score": 82,
            "stable_final_price": 170,
            "standardized_risk_rate": 0.18,
            "dimension_risk_rates": {"waterproof": 0.24, "windproof": 0.18, "durability": 0.12},
            "capacity": "3-4人",
            "use_case": "newbie_weekend",
        },
    ]

    ranked = rank_products(products, scenario="rain_backup", preference="weather_protection")

    assert ranked[0]["product_name"] == "weather safer sample"


def test_multiple_preferences_are_combined_in_user_match_score():
    products = [
        {
            "product_name": "cheap weaker after sale",
            "final_score": 84,
            "data_confidence_score": 82,
            "stable_final_price": 120,
            "standardized_risk_rate": 0.14,
            "dimension_risk_rates": {"return_after_sale": 0.22, "waterproof": 0.12, "windproof": 0.08},
            "recommended_after_sale_service": "支持7天无理由退货(使用后不支持)",
            "capacity": "3-4人",
            "use_case": "newbie_weekend",
        },
        {
            "product_name": "slightly higher better after sale weather",
            "final_score": 82,
            "data_confidence_score": 82,
            "stable_final_price": 140,
            "standardized_risk_rate": 0.1,
            "dimension_risk_rates": {"return_after_sale": 0.01, "waterproof": 0.01, "windproof": 0.01},
            "recommended_after_sale_service": "免费上门退换 闪电退款 京东发货&售后 支持7天无理由退货",
            "capacity": "3-4人",
            "use_case": "newbie_weekend",
        },
    ]

    ranked = rank_products(products, scenario="rain_backup", preference="balanced,lowest_price,after_sale,weather_protection")

    assert ranked[0]["product_name"] == "slightly higher better after sale weather"
    assert ranked[0]["active_preference"] == "lowest_price,after_sale,weather_protection"
    assert any("到手价" in factor for factor in ranked[0]["ranking_factors"])
    assert any("售后" in factor for factor in ranked[0]["ranking_factors"])


def test_rank_products_returns_strict_selection_fields():
    products = [
        {
            "product_name": "core",
            "final_score": 80,
            "data_confidence_score": 82,
            "stable_final_price": 120,
            "standardized_risk_rate": 0.1,
            "dimension_risk_rates": {"setup": 0.01, "return_after_sale": 0.01},
            "recommended_after_sale_service": "免费上门退换 闪电退款 支持7天无理由退货",
            "capacity": "3-4人",
            "use_case": "newbie_weekend",
        }
    ]

    ranked = rank_products(products, scenario="newbie_weekend", preference="lowest_price,after_sale")

    assert ranked[0]["selection_tier"] == "core_match"
    assert ranked[0]["strict_match_score"] > 0
    assert ranked[0]["matched_requirements"]
    assert ranked[0]["unmet_requirements"] == []
    assert "项核心要求满足" in ranked[0]["selection_summary"]


def test_strict_price_and_after_sale_require_all_selected_preferences():
    products = [
        {
            "product_name": "cheap weak after sale",
            "final_score": 84,
            "data_confidence_score": 82,
            "stable_final_price": 120,
            "standardized_risk_rate": 0.14,
            "dimension_risk_rates": {"return_after_sale": 0.22, "setup": 0.02},
            "recommended_after_sale_service": "支持7天无理由退货(使用后不支持)",
            "capacity": "3-4人",
            "use_case": "newbie_weekend",
        },
        {
            "product_name": "slightly higher better after sale",
            "final_score": 82,
            "data_confidence_score": 82,
            "stable_final_price": 140,
            "standardized_risk_rate": 0.1,
            "dimension_risk_rates": {"return_after_sale": 0.01, "setup": 0.01},
            "recommended_after_sale_service": "免费上门退换 闪电退款 京东发货&售后 支持7天无理由退货",
            "capacity": "3-4人",
            "use_case": "newbie_weekend",
        },
    ]

    ranked = rank_products(products, scenario="newbie_weekend", preference="lowest_price,after_sale")

    assert ranked[0]["product_name"] == "slightly higher better after sale"
    assert ranked[0]["selection_tier"] == "core_match"
    assert ranked[1]["selection_tier"] == "partial_match"
    assert any("售后" in item for item in ranked[1]["unmet_requirements"])


def test_weather_preference_requires_low_weather_risk_and_page_claim():
    products = [
        {
            "product_name": "weather claim low risk",
            "final_score": 80,
            "data_confidence_score": 82,
            "stable_final_price": 180,
            "standardized_risk_rate": 0.12,
            "dimension_risk_rates": {"waterproof": 0.01, "windproof": 0.01},
            "capacity": "3-4人",
            "use_case": "newbie_weekend",
            "parameter_analysis": {
                "facts": {"waterproof_index_outer": "2000", "outer_material": "210D牛津布"},
                "scores": {"weather_claim": 76},
            },
        },
        {
            "product_name": "missing weather claim",
            "final_score": 88,
            "data_confidence_score": 82,
            "stable_final_price": 170,
            "standardized_risk_rate": 0.1,
            "dimension_risk_rates": {"waterproof": 0.01, "windproof": 0.01},
            "capacity": "3-4人",
            "use_case": "newbie_weekend",
            "parameter_analysis": {"facts": {}, "scores": {}},
        },
        {
            "product_name": "weather risk",
            "final_score": 88,
            "data_confidence_score": 82,
            "stable_final_price": 160,
            "standardized_risk_rate": 0.2,
            "dimension_risk_rates": {"waterproof": 0.18, "windproof": 0.08},
            "capacity": "3-4人",
            "use_case": "newbie_weekend",
            "parameter_analysis": {
                "facts": {"waterproof_index_outer": "2000", "outer_material": "210D牛津布"},
                "scores": {"weather_claim": 76},
            },
        },
    ]

    ranked = rank_products(products, scenario="rain_backup", preference="weather_protection")

    assert ranked[0]["product_name"] == "weather claim low risk"
    assert ranked[0]["selection_tier"] == "core_match"
    assert all(item["selection_tier"] != "core_match" for item in ranked[1:])


def test_portable_preference_does_not_treat_missing_weight_as_lightweight():
    products = [
        {
            "product_name": "has portable specs",
            "final_score": 80,
            "data_confidence_score": 82,
            "stable_final_price": 180,
            "standardized_risk_rate": 0.12,
            "dimension_risk_rates": {"storage": 0.01, "setup": 0.01},
            "capacity": "2-3人",
            "use_case": "newbie_weekend",
            "parameter_analysis": {
                "facts": {"weight_text": "约3kg", "derived_packed_volume_l": "18L"},
                "scores": {"portability": 76},
            },
        },
        {
            "product_name": "missing portable specs",
            "final_score": 88,
            "data_confidence_score": 82,
            "stable_final_price": 160,
            "standardized_risk_rate": 0.1,
            "dimension_risk_rates": {"storage": 0.01, "setup": 0.01},
            "capacity": "2-3人",
            "use_case": "newbie_weekend",
            "parameter_analysis": {
                "facts": {},
                "scores": {"portability": 80},
                "decision": {"missing_parameters": ["重量"]},
            },
        },
    ]

    ranked = rank_products(products, scenario="hiking_lightweight", preference="portable")

    assert ranked[0]["product_name"] == "has portable specs"
    assert ranked[0]["selection_tier"] == "core_match"
    assert ranked[1]["selection_tier"] != "core_match"


def test_group_party_downgrades_small_capacity_products():
    product = {
        "product_name": "small tent",
        "final_score": 88,
        "data_confidence_score": 82,
        "stable_final_price": 160,
        "standardized_risk_rate": 0.1,
        "dimension_risk_rates": {"space": 0.01},
        "capacity": "2-3人",
        "use_case": "newbie_weekend",
        "parameter_analysis": {"facts": {"derived_floor_area_m2": "3.2㎡"}, "scores": {"space": 72}},
    }

    result = selection_tier_and_score(evaluate_selection_requirements(product, [product], "group_party", ["gift_package"]))

    assert result["selection_tier"] == "fallback"
    assert any("多人" in item or "空间" in item for item in result["unmet_requirements"])


def test_partial_and_fallback_results_keep_unmet_requirements_when_core_matches_are_sparse():
    products = [
        {
            "product_name": "partial",
            "final_score": 80,
            "data_confidence_score": 82,
            "stable_final_price": 120,
            "standardized_risk_rate": 0.1,
            "dimension_risk_rates": {"return_after_sale": 0.2, "setup": 0.01},
            "recommended_after_sale_service": "支持7天无理由退货(使用后不支持)",
            "capacity": "3-4人",
            "use_case": "newbie_weekend",
        },
        {
            "product_name": "fallback",
            "final_score": 78,
            "data_confidence_score": 82,
            "stable_final_price": 300,
            "standardized_risk_rate": 0.2,
            "dimension_risk_rates": {"return_after_sale": 0.2, "setup": 0.01},
            "recommended_after_sale_service": "支持7天无理由退货(使用后不支持)",
            "capacity": "3-4人",
            "use_case": "newbie_weekend",
        },
    ]

    ranked = rank_products(products, scenario="newbie_weekend", preference="lowest_price,after_sale")

    assert len(ranked) == 2
    assert ranked[0]["selection_tier"] == "partial_match"
    assert ranked[0]["unmet_requirements"]
    assert ranked[1]["selection_tier"] == "fallback"

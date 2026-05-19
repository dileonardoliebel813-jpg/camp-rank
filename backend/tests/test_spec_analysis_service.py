import json
from types import SimpleNamespace

from app.services.spec_analysis_service import build_parameter_analysis


def _spec(**overrides):
    data = {
        "raw_specs_json": json.dumps(
            {
                "source_product_name": "狼行者 户外帐篷公园休闲遮阳篷防晒防水沙滩野外精致露营装备",
                "expanded_size_text": "210*150*110CM",
                "outer_material": "聚酯纤维",
                "weight_text": "约3kg",
                "setup_type": "弹簧帐篷",
                "claimed_functions": ["遮阳", "防晒"],
            },
            ensure_ascii=False,
        ),
        "waterproof_index_outer": None,
        "waterproof_index_floor": None,
        "weight_kg": 3.0,
        "expanded_length_cm": 210,
        "expanded_width_cm": 150,
        "expanded_height_cm": 110,
        "floor_area_m2": 3.15,
        "packed_volume_l": None,
        "pole_material": "玻璃纤维杆",
        "outer_material": "聚酯纤维",
        "setup_type": "弹簧帐篷",
        "tent_type": "单层弹簧帐篷",
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_parameter_decision_explains_area_and_missing_fields():
    analysis = build_parameter_analysis(_spec())
    decision = analysis["decision"]

    assert "约 3.15㎡" in decision["space_judgment"]
    assert "适合 1-2 人短途休闲" in decision["space_judgment"]
    assert decision["missing_parameters"] == ["防水指数"]
    assert "防水指数" in decision["missing_parameter_text"]
    assert "页面标称展开尺寸：210*150*110CM" in decision["raw_parameter_facts"]


def test_parameter_decision_marks_missing_specs_as_pending_confirmation():
    analysis = build_parameter_analysis(None)
    decision = analysis["decision"]

    assert analysis["has_specs"] is False
    assert "商品参数未接入" in decision["space_judgment"]
    assert decision["missing_parameters"] == ["防水指数", "重量", "材质", "搭建方式"]


def test_parameter_analysis_treats_null_optional_text_fields_as_missing():
    analysis = build_parameter_analysis(
        _spec(
            pole_material=None,
            outer_material=None,
            tent_type=None,
            raw_specs_json=json.dumps(
                {
                    "source_product_name": "真实页面参数不完整的速开帐篷",
                    "setup_type": "全自动速开",
                },
                ensure_ascii=False,
            ),
        )
    )

    assert analysis["has_specs"] is True
    assert analysis["facts"]["pole_material"] == ""
    assert analysis["cautions"]

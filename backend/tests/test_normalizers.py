from app.ingestion.normalizers import (
    calculate_floor_area_m2,
    calculate_packed_volume_l,
    normalize_bool,
    normalize_platform,
    normalize_price,
    normalize_size_to_cm_tuple,
    normalize_waterproof_index,
    normalize_weight_to_kg,
)


def test_normalize_price():
    assert normalize_price("￥299") == 299
    assert normalize_price("299元") == 299
    assert normalize_price("299.00") == 299
    assert normalize_price(None) is None


def test_normalize_weight_to_kg():
    assert normalize_weight_to_kg("3000g") == 3
    assert normalize_weight_to_kg("3kg") == 3
    assert normalize_weight_to_kg("约 2.8 千克") == 2.8
    assert normalize_weight_to_kg("2.8KG") == 2.8


def test_normalize_waterproof_index():
    assert normalize_waterproof_index("PU2000mm") == 2000
    assert normalize_waterproof_index("2000mm") == 2000
    assert normalize_waterproof_index("2000-3000mm") == 2500
    assert normalize_waterproof_index("防水指数3000") == 3000


def test_size_and_derived_metrics():
    assert normalize_size_to_cm_tuple("210*150*120cm") == (210, 150, 120)
    assert normalize_size_to_cm_tuple("210×150×120cm") == (210, 150, 120)
    assert normalize_size_to_cm_tuple("2.1m*1.5m*1.2m") == (210, 150, 120)
    assert normalize_size_to_cm_tuple("210 x 150 x 120 cm") == (210, 150, 120)
    assert calculate_floor_area_m2("210*150*120cm") == 3.15
    assert calculate_packed_volume_l("50*20*20cm") == 20


def test_bool_and_platform_normalization():
    assert normalize_bool("是") is True
    assert normalize_bool("否") is False
    assert normalize_bool("支持") is True
    assert normalize_bool("不支持") is False
    assert normalize_bool("true") is True
    assert normalize_bool("0") is False
    assert normalize_platform("京东") == "JD"
    assert normalize_platform("tmall") == "TMALL"
    assert normalize_platform("unknown") == "OTHER"


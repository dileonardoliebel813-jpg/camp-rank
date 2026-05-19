import json
from pathlib import Path

from app.ingestion.platform_adapters import JDAdapter, PddAdapter, SMZDMAdapter, TaobaoAdapter
from app.ingestion.sdk_clients import JDUnionClient, PddOpenClient, SMZDMOpenClient, TaobaoTopClient


SAMPLES = Path(__file__).resolve().parents[1] / "data" / "official_response_samples"


def _load(name: str):
    return json.loads((SAMPLES / name).read_text(encoding="utf-8"))


def test_jd_official_sample_normalizes_to_unified_fields():
    items = JDUnionClient().normalize_response(_load("jd_goods_search_response.sample.json"))
    assert items[0]["platform_product_id"] == "jd-10001"
    assert items[0]["title"]
    assert items[0]["current_price"] == "499.00"
    payload = JDAdapter().normalize({"items": items, "limit": 5, "live_mode": True})
    assert payload["platform_products"][0]["platform"] == "JD"
    assert payload["product_prices"][0]["current_price"] == "499.00"


def test_smzdm_official_sample_normalizes_to_unified_fields():
    items = SMZDMOpenClient().normalize_response(_load("smzdm_search_response.sample.json"))
    assert items[0]["article_id"] == "smzdm-20001"
    assert items[0]["source_platform"] == "京东"
    payload = SMZDMAdapter().normalize({"deals": items, "limit": 5, "live_mode": True})
    assert payload["platform_products"][0]["platform"] == "SMZDM"
    assert payload["product_prices"][0]["promotion_text"]


def test_taobao_official_sample_normalizes_to_unified_fields():
    items = TaobaoTopClient().normalize_response(_load("taobao_material_search_response.sample.json"))
    assert items[0]["platform_product_id"] == "tb-30001"
    assert items[0]["shop_type"] == "tmall"
    payload = TaobaoAdapter().normalize({"items": items, "limit": 5, "live_mode": True})
    assert payload["platform_products"][0]["shop_name"] == "骆驼户外旗舰店"
    assert payload["product_prices"][0]["current_price"] == "389.00"


def test_pdd_official_sample_normalizes_and_converts_cents_to_yuan():
    items = PddOpenClient().normalize_response(_load("pdd_goods_search_response.sample.json"))
    assert items[0]["platform_product_id"] == "pdd-sign-40001"
    assert items[0]["current_price"] == 269.0
    assert items[0]["coupon_amount"] == 20.0
    payload = PddAdapter().normalize({"goods": items, "limit": 5, "live_mode": True})
    assert payload["platform_products"][0]["platform"] == "PDD"
    assert payload["product_prices"][0]["current_price"] == 269.0


def test_missing_fields_produce_warnings_instead_of_crashing():
    items = JDUnionClient().normalize_response({"items": [{"skuId": "missing-price"}]})
    payload = JDAdapter().normalize({"items": items, "limit": 5, "live_mode": True})
    assert payload["platform_products"]
    assert any("missing" in warning for warning in payload["_warnings"])

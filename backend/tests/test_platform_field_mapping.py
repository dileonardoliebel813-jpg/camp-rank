from app.ingestion.platform_adapters import JDAdapter, PddAdapter, RedBookAdapter, SMZDMAdapter, TaobaoAdapter


def test_jd_raw_fields_map_to_unified_fields(monkeypatch):
    monkeypatch.setenv("JD_API_ENABLED", "false")
    adapter = JDAdapter()
    raw = {
        "sku_id": "JD-001",
        "ware_name": "JD Tent",
        "image_url": "https://example.com/jd.jpg",
        "price": "699",
        "coupon_amount": "30",
        "shop_name": "JD Shop",
        "is_self_operated": True,
        "product_url": "https://example.com/jd",
    }
    product = adapter.map_raw_item_to_platform_product(raw)
    price = adapter.map_raw_item_to_price(raw)
    benefit = adapter.map_raw_item_to_benefit(raw)
    assert product["platform_product_id"] == "JD-001"
    assert product["title"] == "JD Tent"
    assert price["current_price"] == "699"
    assert price["shop_coupon_amount"] == "30"
    assert benefit["self_operated"] is True


def test_smzdm_raw_fields_map_to_unified_fields(monkeypatch):
    monkeypatch.setenv("SMZDM_API_ENABLED", "false")
    adapter = SMZDMAdapter()
    raw = {
        "article_id": "SMZDM-001",
        "title": "SMZDM Tent Deal",
        "mall": "JD",
        "price": "599",
        "content": "deal details",
        "article_url": "https://example.com/deal",
        "publish_time": "2026-04-01 08:00:00",
    }
    product = adapter.map_raw_item_to_platform_product(raw)
    price = adapter.map_raw_item_to_price(raw)
    assert product["platform_product_id"] == "SMZDM-001"
    assert product["platform"] == "SMZDM"
    assert product["shop_name"] == "JD"
    assert price["current_price"] == "599"
    assert price["promotion_text"] == "deal details"
    assert price["price_update_time"] == "2026-04-01 08:00:00"


def test_taobao_pdd_redbook_missing_fields_do_not_interrupt(monkeypatch):
    monkeypatch.setenv("TAOBAO_API_ENABLED", "false")
    monkeypatch.setenv("PDD_API_ENABLED", "false")
    monkeypatch.setenv("REDBOOK_API_ENABLED", "false")
    assert TaobaoAdapter().map_raw_item_to_platform_product({})["platform"] == "TAOBAO"
    assert PddAdapter().map_raw_item_to_platform_product({})["platform"] == "PDD"
    note = RedBookAdapter().map_raw_item_to_redbook_note({})
    assert note["title"] is None


def test_missing_fields_generate_warning(monkeypatch):
    monkeypatch.setenv("JD_API_ENABLED", "false")
    adapter = JDAdapter()
    adapter.map_raw_item_to_platform_product({"sku_id": "JD-MISSING"})
    warnings = adapter.pop_warnings()
    assert any("missing title" in warning for warning in warnings)

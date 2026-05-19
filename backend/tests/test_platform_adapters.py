from pathlib import Path

from app.ingestion.platform_adapters import JDAdapter, PddAdapter, RedBookAdapter, SMZDMAdapter, TaobaoAdapter


ROOT = Path(__file__).resolve().parents[1]


def test_jd_adapter_default_offline_reads_local_json(monkeypatch):
    monkeypatch.setenv("JD_API_ENABLED", "false")
    adapter = JDAdapter(str(ROOT / "data" / "real_samples" / "jd_tents_sample.json"))
    raw = adapter.fetch_raw_data("tent")
    normalized = adapter.normalize(raw)
    assert adapter.api_enabled is False
    assert normalized["platform_products"][0]["platform"] == "JD"
    assert normalized["product_prices"][0]["platform_product_id"] == "JD-SAMPLE-CLOUDUP2"


def test_smzdm_adapter_default_offline_reads_local_json(monkeypatch):
    monkeypatch.setenv("SMZDM_API_ENABLED", "false")
    adapter = SMZDMAdapter(str(ROOT / "data" / "real_samples" / "smzdm_tents_sample.json"))
    raw = adapter.fetch_raw_data("tent")
    normalized = adapter.normalize(raw)
    assert adapter.api_enabled is False
    assert normalized["platform_products"][0]["platform"] == "SMZDM"


def test_other_platform_adapters_do_not_network_by_default(monkeypatch):
    monkeypatch.setenv("TAOBAO_API_ENABLED", "false")
    monkeypatch.setenv("PDD_API_ENABLED", "false")
    monkeypatch.setenv("REDBOOK_API_ENABLED", "false")
    assert TaobaoAdapter().fetch_raw_data("tent") == {}
    assert PddAdapter().fetch_raw_data("tent") == {}
    assert RedBookAdapter().fetch_raw_data("tent") == {}


from pathlib import Path

import pytest

from app.ingestion.platform_adapters import JDAdapter, PddAdapter, RedBookAdapter, SMZDMAdapter, TaobaoAdapter
from app.ingestion.sdk_clients import OfficialAPIConfigError


ADAPTER_DIR = Path(__file__).resolve().parents[1] / "app" / "ingestion" / "platform_adapters"


def test_jd_live_missing_config_errors(monkeypatch):
    monkeypatch.setenv("JD_API_ENABLED", "true")
    monkeypatch.setenv("JD_BASE_URL", "https://official.example/router")
    monkeypatch.setenv("JD_API_METHOD_SEARCH", "jingdong.union.search")
    monkeypatch.delenv("JD_APP_KEY", raising=False)
    monkeypatch.delenv("JD_APP_SECRET", raising=False)
    with pytest.raises(OfficialAPIConfigError, match="JD_APP_KEY"):
        JDAdapter().fetch_live("帐篷")


def test_smzdm_live_missing_config_errors(monkeypatch):
    monkeypatch.setenv("SMZDM_API_ENABLED", "true")
    monkeypatch.setenv("SMZDM_BASE_URL", "https://official.example")
    monkeypatch.delenv("SMZDM_API_KEY", raising=False)
    with pytest.raises(OfficialAPIConfigError, match="SMZDM_API_KEY"):
        SMZDMAdapter().fetch_live("帐篷")


@pytest.mark.parametrize("adapter_class", [TaobaoAdapter, PddAdapter, RedBookAdapter])
def test_disabled_live_adapters_do_not_network(adapter_class):
    with pytest.raises(OfficialAPIConfigError, match="API_ENABLED=false"):
        adapter_class().fetch_live("帐篷")


def test_adapters_do_not_request_cookie_account_password_or_captcha_fields():
    combined = "\n".join(path.read_text(encoding="utf-8") for path in ADAPTER_DIR.glob("*.py"))
    forbidden = [
        "params={'cookie'",
        'params={"cookie"',
        ".get('cookie'",
        '.get("cookie"',
        "password=",
        "account=",
        "captcha=",
    ]
    for token in forbidden:
        assert token not in combined

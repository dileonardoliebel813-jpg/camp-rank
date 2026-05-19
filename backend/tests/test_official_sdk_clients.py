import pytest

from app.ingestion.sdk_clients import (
    JDUnionClient,
    OfficialAPIConfigError,
    PddOpenClient,
    RedBookAuthorizedClient,
    SMZDMOpenClient,
    TaobaoTopClient,
    UnsupportedAuthorizedSourceError,
)


@pytest.mark.parametrize(
    "client_class,env_name",
    [
        (JDUnionClient, "JD_API_ENABLED"),
        (SMZDMOpenClient, "SMZDM_API_ENABLED"),
        (TaobaoTopClient, "TAOBAO_API_ENABLED"),
        (PddOpenClient, "PDD_API_ENABLED"),
        (RedBookAuthorizedClient, "REDBOOK_API_ENABLED"),
    ],
)
def test_default_api_disabled_does_not_network(monkeypatch, client_class, env_name):
    monkeypatch.setenv(env_name, "false")
    client = client_class()

    def fail_request(*args, **kwargs):  # pragma: no cover - called only if guard breaks
        raise AssertionError("request should not be called when official API is disabled")

    monkeypatch.setattr(client, "request", fail_request)
    with pytest.raises((OfficialAPIConfigError, UnsupportedAuthorizedSourceError)):
        client.smoke_test("帐篷", 1)


def test_jd_missing_app_key_app_secret_errors_clearly(monkeypatch):
    monkeypatch.setenv("JD_API_ENABLED", "true")
    monkeypatch.setenv("JD_BASE_URL", "https://official.example/router")
    monkeypatch.setenv("JD_API_METHOD_SEARCH", "jingdong.union.search")
    monkeypatch.delenv("JD_APP_KEY", raising=False)
    monkeypatch.delenv("JD_APP_SECRET", raising=False)
    with pytest.raises(OfficialAPIConfigError, match="JD_APP_KEY"):
        JDUnionClient().search_goods("帐篷", 1)


def test_taobao_missing_required_fields_errors_clearly(monkeypatch):
    monkeypatch.setenv("TAOBAO_API_ENABLED", "true")
    monkeypatch.setenv("TAOBAO_BASE_URL", "https://eco.taobao.example/router")
    monkeypatch.delenv("TAOBAO_APP_KEY", raising=False)
    with pytest.raises(OfficialAPIConfigError, match="TAOBAO_APP_KEY"):
        TaobaoTopClient().search_material("帐篷", 1)


def test_pdd_missing_required_fields_errors_clearly(monkeypatch):
    monkeypatch.setenv("PDD_API_ENABLED", "true")
    monkeypatch.setenv("PDD_BASE_URL", "https://gw-api.pinduoduo.example/router")
    monkeypatch.delenv("PDD_CLIENT_ID", raising=False)
    with pytest.raises(OfficialAPIConfigError, match="PDD_CLIENT_ID"):
        PddOpenClient().search_goods("帐篷", 1)


def test_smzdm_missing_api_key_errors_clearly(monkeypatch):
    monkeypatch.setenv("SMZDM_API_ENABLED", "true")
    monkeypatch.setenv("SMZDM_BASE_URL", "https://open.smzdm.example")
    monkeypatch.delenv("SMZDM_API_KEY", raising=False)
    with pytest.raises(OfficialAPIConfigError, match="SMZDM_API_KEY"):
        SMZDMOpenClient().search_deals("帐篷", 1)


def test_redbook_enabled_without_authorized_method_is_unsupported(monkeypatch):
    monkeypatch.setenv("REDBOOK_API_ENABLED", "true")
    monkeypatch.setenv("REDBOOK_APP_ID", "app")
    monkeypatch.setenv("REDBOOK_APP_SECRET", "secret")
    monkeypatch.setenv("REDBOOK_BASE_URL", "https://authorized.example")
    with pytest.raises(UnsupportedAuthorizedSourceError, match="authorized API is not implemented"):
        RedBookAuthorizedClient().smoke_test("帐篷", 1)

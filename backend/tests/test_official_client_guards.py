from pathlib import Path

from app.ingestion.fetch_service import fetch_and_import


SDK_DIR = Path(__file__).resolve().parents[1] / "app" / "ingestion" / "sdk_clients"


def test_clients_do_not_request_cookie_password_or_captcha_fields():
    combined = "\n".join(path.read_text(encoding="utf-8").lower() for path in SDK_DIR.glob("*.py"))
    forbidden = [
        "os.getenv(\"cookie",
        "os.getenv('cookie",
        "password=",
        "account=",
        "captcha=",
        ".get(\"cookie",
        ".get('cookie",
    ]
    for token in forbidden:
        assert token not in combined


def test_live_false_without_input_does_not_call_request(db_session, monkeypatch):
    def fail_fetch_live(*args, **kwargs):  # pragma: no cover - called only if guard breaks
        raise AssertionError("fetch_live should not run for live=false")

    monkeypatch.setattr("app.ingestion.platform_adapters.smzdm_adapter.SMZDMAdapter.fetch_live", fail_fetch_live)
    report = fetch_and_import(db_session, source="smzdm", keyword="帐篷", live=False)
    assert report.errors
    assert "input_path" in report.errors[0]


def test_dry_run_does_not_write_database(db_session):
    before = len(db_session.identity_map)
    report = fetch_and_import(
        db_session,
        source="jd",
        keyword="帐篷",
        limit=1,
        live=False,
        input_path=str(Path(__file__).resolve().parents[1] / "data" / "real_samples" / "jd_tents_sample.json"),
        dry_run=True,
    )
    assert not report.errors
    assert report.dry_run is True
    assert report.imported_count == 0
    assert len(db_session.identity_map) >= before


def test_fetch_report_does_not_contain_secrets(db_session, monkeypatch):
    monkeypatch.setenv("JD_APP_SECRET", "super-secret-value")
    report = fetch_and_import(db_session, source="jd", keyword="帐篷", live=True)
    text = report.model_dump_json()
    assert "super-secret-value" not in text

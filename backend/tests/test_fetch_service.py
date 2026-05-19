from pathlib import Path

from app.ingestion.fetch_service import fetch_and_import


ROOT = Path(__file__).resolve().parents[1]


def test_fetch_service_local_input_imports(db_session, monkeypatch):
    monkeypatch.setenv("SMZDM_API_ENABLED", "false")
    report = fetch_and_import(
        db_session,
        source="smzdm",
        keyword="帐篷",
        limit=20,
        live=False,
        input_path=str(ROOT / "data" / "real_samples" / "smzdm_tents_sample.json"),
    )
    assert report.source == "smzdm"
    assert report.live_mode is False
    assert report.fetched_items == 1
    assert report.imported_products >= 1
    assert report.started_at is not None
    assert report.finished_at is not None
    assert not report.errors


def test_fetch_service_local_without_input_reports_error(db_session):
    report = fetch_and_import(db_session, source="smzdm", keyword="帐篷", live=False)
    assert report.errors
    assert "input_path" in report.errors[0]


def test_fetch_service_live_disabled_reports_error(db_session, monkeypatch):
    monkeypatch.setenv("SMZDM_API_ENABLED", "false")
    report = fetch_and_import(db_session, source="smzdm", keyword="帐篷", live=True)
    assert report.live_mode is True
    assert report.errors
    assert "SMZDM_API_ENABLED=false" in report.errors[0]


def test_fetch_service_unsupported_source_reports_error(db_session):
    report = fetch_and_import(db_session, source="unknown", keyword="帐篷", live=True)
    assert report.errors
    assert "Unsupported source" in report.errors[0]


def test_fetch_report_fields_complete(db_session):
    report = fetch_and_import(db_session, source="jd", keyword="帐篷", live=False)
    data = report.model_dump()
    for field in (
        "source",
        "keyword",
        "live_mode",
        "requested_limit",
        "fetched_items",
        "imported_products",
        "imported_comments",
        "imported_redbook_notes",
        "warnings",
        "errors",
        "started_at",
        "finished_at",
    ):
        assert field in data

from pathlib import Path
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.ingestion.data_quality import build_quality_records_from_payload, summarize_import_quality
from app.ingestion.import_report import FetchReport
from app.ingestion.platform_adapters import JDAdapter, PddAdapter, RedBookAdapter, SMZDMAdapter, TaobaoAdapter
from app.ingestion.sdk_clients import OfficialAPIError


ADAPTERS = {
    "jd": JDAdapter,
    "smzdm": SMZDMAdapter,
    "taobao": TaobaoAdapter,
    "pdd": PddAdapter,
    "redbook": RedBookAdapter,
}

LAST_FETCH_REPORT: FetchReport | None = None


def _count_raw_items(raw_data: dict[str, Any]) -> int:
    for key in ("items", "deals", "platform_products", "redbook_notes"):
        value = raw_data.get(key)
        if isinstance(value, list):
            return len(value)
    for key in ("data", "result"):
        value = raw_data.get(key)
        if isinstance(value, list):
            return len(value)
        if isinstance(value, dict):
            for nested_key in ("items", "list", "deals", "goods"):
                nested = value.get(nested_key)
                if isinstance(nested, list):
                    return len(nested)
    return 0


def _save_normalized_json(source: str, normalized: dict[str, Any]) -> str:
    output_dir = Path(__file__).resolve().parents[2] / "data" / "real_samples"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"live_fetch_{source}_{timestamp}.json"
    with path.open("w", encoding="utf-8") as file:
        json.dump(normalized, file, ensure_ascii=False, indent=2, default=str)
    return str(path)


def _field_summary(normalized: dict[str, Any], platform: str) -> dict:
    records = build_quality_records_from_payload(normalized)
    return summarize_import_quality(records, platform.upper())


def fetch_and_import(
    db: Session,
    source: str,
    keyword: str,
    limit: int = 20,
    live: bool = False,
    input_path: str | None = None,
    dry_run: bool = False,
    save_json: bool = False,
) -> FetchReport:
    global LAST_FETCH_REPORT

    source_key = source.strip().lower()
    report = FetchReport(source=source_key, keyword=keyword, live_mode=live, requested_limit=limit, dry_run=dry_run)
    adapter_class = ADAPTERS.get(source_key)
    if adapter_class is None:
        report.error(f"Unsupported source '{source}'. Supported sources: {', '.join(sorted(ADAPTERS))}.")
        LAST_FETCH_REPORT = report.finish()
        return LAST_FETCH_REPORT

    try:
        if live:
            adapter = adapter_class()
            raw_data = adapter.fetch_live(keyword=keyword, limit=limit)
        else:
            if not input_path:
                report.error("live=false requires input_path. Local file import is not real network collection.")
                LAST_FETCH_REPORT = report.finish()
                return LAST_FETCH_REPORT
            adapter = adapter_class(str(Path(input_path)))
            raw_data = adapter.fetch_raw_data(keyword=keyword, limit=limit)
            report.warn("live=false: imported from local file only; this is not real network collection.")
        if not isinstance(raw_data, dict):
            raise RuntimeError("adapter returned non-dict raw_data")
        report.fetched_count = min(_count_raw_items(raw_data), limit)
        if raw_data.get("warning"):
            report.warn(str(raw_data["warning"]))
        normalized = adapter.normalize(raw_data)
        report.normalized_count = min(_count_raw_items(normalized), limit)
        report.field_completeness_summary = _field_summary(normalized, source_key)
        for warning in normalized.get("_warnings", []):
            report.warn(str(warning))
        if save_json:
            report.saved_json_path = _save_normalized_json(source_key, normalized)
        if dry_run:
            for warning in adapter.validate(normalized):
                report.warn(warning)
        else:
            import_report = adapter.import_to_db(db, normalized)
            report.imported_count = (
                import_report.imported_platform_products + import_report.updated_records
            )
            report.imported_comments = import_report.imported_comments
            report.imported_redbook_notes = import_report.imported_redbook_notes
            report.field_completeness_summary = import_report.field_completeness_summary
            for warning in import_report.warnings:
                report.warn(warning)
            for error in import_report.errors:
                report.error(error)
    except OfficialAPIError as exc:
        db.rollback()
        report.error(str(exc))
        report.set_official_error(getattr(exc, "error_code", None), getattr(exc, "error_message", None) or str(exc))
    except Exception as exc:  # noqa: BLE001 - service returns a report instead of hiding collection failures
        db.rollback()
        report.error(str(exc))

    LAST_FETCH_REPORT = report.finish()
    return LAST_FETCH_REPORT


def get_last_fetch_report() -> dict:
    if LAST_FETCH_REPORT is None:
        return {"status": "empty", "last_fetch_report": None}
    return {"status": "ok", "last_fetch_report": LAST_FETCH_REPORT}

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


LAST_QUALITY_REPORT: dict[str, Any] | None = None


def _report_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "import_reports" / "latest_import_report.json"


def save_last_quality_report(report: dict[str, Any]) -> None:
    global LAST_QUALITY_REPORT
    LAST_QUALITY_REPORT = report
    path = _report_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def get_last_quality_report() -> dict[str, Any]:
    if LAST_QUALITY_REPORT is not None:
        return {"status": "ok", "quality_report": LAST_QUALITY_REPORT}
    path = _report_path()
    if path.exists():
        return {"status": "ok", "quality_report": json.loads(path.read_text(encoding="utf-8"))}
    return {"status": "empty", "quality_report": None}

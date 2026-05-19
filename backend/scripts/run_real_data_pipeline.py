import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.ingestion.import_service import import_from_json  # noqa: E402
from app.ingestion.platform_adapters import JDAdapter, PddAdapter, RedBookAdapter, SMZDMAdapter, TaobaoAdapter  # noqa: E402
from app.models import *  # noqa: F401,F403,E402
from app.services.comment_analysis_service import analyze_and_update_comments, analyze_and_update_redbook_notes  # noqa: E402
from app.services.sample_data_service import ensure_sample_data  # noqa: E402
from app.services.scoring_service import calculate_all_scores  # noqa: E402


ADAPTERS = {
    "jd": JDAdapter,
    "smzdm": SMZDMAdapter,
    "taobao": TaobaoAdapter,
    "pdd": PddAdapter,
    "redbook": RedBookAdapter,
}


def _resolve_backend_path(path_text: str) -> str:
    path = Path(path_text)
    if path.is_absolute():
        return str(path)
    return str((ROOT / path).resolve())


def _resolve_backend_path_obj(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path.resolve()
    return (ROOT / path).resolve()


def _sqlite_database_path() -> Path | None:
    if engine.url.get_backend_name() != "sqlite":
        return None
    database = engine.url.database
    if not database or database == ":memory:":
        return None
    path = Path(database)
    if path.is_absolute():
        return path.resolve()
    return (ROOT / path).resolve()


def _reset_sqlite_database(backup_dir_text: str) -> None:
    db_path = _sqlite_database_path()
    if db_path is None:
        print("Database reset skipped: current database is not a file-backed SQLite database.")
        return
    if not db_path.exists():
        print(f"Database reset skipped: {db_path} does not exist yet.")
        return

    backup_dir = _resolve_backend_path_obj(backup_dir_text)
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{db_path.stem}_backup_{timestamp}{db_path.suffix}"

    engine.dispose()
    shutil.copy2(db_path, backup_path)
    db_path.unlink()
    print(f"Backed up existing database: {backup_path}")
    print(f"Reset SQLite database: {db_path}")


def _print_json(title: str, data) -> None:
    print(title)
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local real-data import, analysis, and scoring pipeline.")
    parser.add_argument("--json", dest="json_path", help="Unified local JSON payload.")
    parser.add_argument("--adapter", choices=sorted(ADAPTERS), help="Platform adapter for platform-shaped local JSON.")
    parser.add_argument("--input", dest="input_path", help="Local adapter input JSON.")
    parser.add_argument("--platform", required=True, help="Platform label such as JD or SMZDM.")
    parser.add_argument(
        "--no-sample-data",
        action="store_true",
        help="Do not seed historical sample/mock data before importing the real payload.",
    )
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Back up and recreate the SQLite database before importing this payload.",
    )
    parser.add_argument(
        "--backup-dir",
        default="data/import_reports",
        help="Backup directory used with --reset-db. Relative paths are resolved under backend/.",
    )
    args = parser.parse_args()

    if args.json_path and args.adapter:
        parser.error("Use either --json or --adapter, not both.")
    if args.adapter and not args.input_path:
        parser.error("--adapter requires --input.")
    if not args.json_path and not args.adapter:
        parser.error("Provide --json or --adapter with --input.")

    if args.reset_db:
        _reset_sqlite_database(args.backup_dir)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if args.no_sample_data:
            print("Sample data seeding skipped for this import.")
        else:
            ensure_sample_data(db)
        if args.json_path:
            report = import_from_json(
                db,
                _resolve_backend_path(args.json_path),
                source_name=f"pipeline_{args.platform.lower()}_json",
            )
            report.platform = args.platform.upper()
        else:
            adapter = ADAPTERS[args.adapter](_resolve_backend_path(args.input_path))
            raw_data = adapter.fetch_raw_data(keyword="")
            normalized = adapter.normalize(raw_data)
            report = adapter.import_to_db(db, normalized)

        comment_result = analyze_and_update_comments(db)
        redbook_result = analyze_and_update_redbook_notes(db)
        score_result = calculate_all_scores(db, seed_sample_data=not args.no_sample_data)

        report_data = report.model_dump() if hasattr(report, "model_dump") else report.dict()
        _print_json("ImportReport:", report_data)
        final_stats = {
            "imported_products": report.imported_platform_products + report.updated_records,
            "analyzed_comments": comment_result["comment_count"],
            "analyzed_redbook_notes": redbook_result["note_count"],
            "updated_scores": score_result["updated_product_scores"],
            "updated_platform_offers": score_result["updated_platform_offers"],
            "warnings": report.warnings,
            "field_completeness": report.field_completeness_summary,
        }
        _print_json("Pipeline final stats:", final_stats)
        return 1 if report.errors else 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

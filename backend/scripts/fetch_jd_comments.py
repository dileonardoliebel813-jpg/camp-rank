from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.ingestion.jd_comment_importer import import_jd_comments_json  # noqa: E402
from app.ingestion.jd_public_comments import JDPublicCommentFetcher  # noqa: E402


def _report_to_dict(report):
    return report.model_dump() if hasattr(report, "model_dump") else report.dict()


def run_cli(
    argv: list[str] | None = None,
    fetcher_factory=JDPublicCommentFetcher,
    importer=import_jd_comments_json,
    db_session_factory=None,
) -> int:
    parser = argparse.ArgumentParser(description="Fetch low-frequency public JD SKU comment summaries.")
    parser.add_argument("--sku-id", required=True)
    parser.add_argument("--max-pages", type=int, default=5)
    parser.add_argument("--page-size", type=int, default=10)
    parser.add_argument("--delay", type=float, default=2.0)
    parser.add_argument("--save-only", action="store_true", help="Fetch and save JSON only. This is the default.")
    parser.add_argument("--import-db", action="store_true", help="Import the saved JSON into the local database.")
    args = parser.parse_args(argv)

    fetcher = fetcher_factory()
    result = fetcher.fetch_comments(
        sku_id=args.sku_id,
        max_pages=args.max_pages,
        page_size=args.page_size,
        delay_seconds=args.delay,
    )
    saved_json_path = fetcher.save_comments_json(args.sku_id, result.get("comments", []))
    output = {
        "source_name": "jd_public_comment",
        "sku_id": args.sku_id,
        "fetched_count": len(result.get("comments", [])),
        "saved_json_path": saved_json_path,
        "warnings": result.get("warnings", []),
        "errors": result.get("errors", []),
    }

    if args.import_db:
        from app.database import Base, SessionLocal, engine  # noqa: WPS433
        import app.models  # noqa: F401,WPS433
        from app.services.sample_data_service import ensure_sample_data  # noqa: WPS433

        if db_session_factory is None:
            Base.metadata.create_all(bind=engine)
            db = SessionLocal()
            should_close_db = True
        else:
            db = db_session_factory()
            should_close_db = False
        try:
            if db_session_factory is None:
                ensure_sample_data(db)
            import_report = importer(db, saved_json_path)
            output["import_report"] = _report_to_dict(import_report)
            if import_report.errors:
                output["errors"].extend(import_report.errors)
            if import_report.warnings:
                output["warnings"].extend(import_report.warnings)
        finally:
            if should_close_db:
                db.close()

    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))
    if not output["errors"]:
        print("\nNext steps after importing:")
        print("  python scripts/analyze_comments.py")
        print("  python scripts/calculate_scores.py")
    return 1 if output["errors"] else 0


def main() -> int:
    return run_cli()


if __name__ == "__main__":
    raise SystemExit(main())

from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.ingestion.fetch_service import ADAPTERS, fetch_and_import  # noqa: E402
from app.models import *  # noqa: F401,F403,E402
from app.services.sample_data_service import ensure_sample_data  # noqa: E402


def _print_report(report) -> None:
    data = report.model_dump() if hasattr(report, "model_dump") else report.dict()
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
    if not report.errors:
        print("\nNext steps:")
        print("  python scripts/analyze_comments.py")
        print("  python scripts/calculate_scores.py")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch or import CampRank real data through platform adapters.")
    parser.add_argument("--source", required=True, choices=sorted(ADAPTERS))
    parser.add_argument("--keyword", required=True)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--live", action="store_true", help="Use configured official/open API source for real network fetch.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and normalize without writing to the database.")
    parser.add_argument("--save-json", action="store_true", help="Save normalized official API results under data/real_samples.")
    parser.add_argument("--input", dest="input_path", help="Local JSON input path for live=false imports.")
    args = parser.parse_args()

    if not args.live and not args.input_path:
        parser.error("Without --live, --input is required. Local imports are not real network collection.")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_sample_data(db)
        report = fetch_and_import(
            db,
            source=args.source,
            keyword=args.keyword,
            limit=args.limit,
            live=args.live,
            input_path=args.input_path,
            dry_run=args.dry_run,
            save_json=args.save_json,
        )
        _print_report(report)
        return 1 if report.errors else 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

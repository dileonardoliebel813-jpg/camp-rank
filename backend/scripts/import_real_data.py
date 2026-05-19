from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.ingestion.import_service import import_from_csv_folder, import_from_json  # noqa: E402
from app.ingestion.platform_adapters import JDAdapter, PddAdapter, RedBookAdapter, SMZDMAdapter, TaobaoAdapter  # noqa: E402
from app.models import *  # noqa: F401,F403,E402
from app.services.sample_data_service import ensure_sample_data  # noqa: E402


ADAPTERS = {
    "jd": JDAdapter,
    "smzdm": SMZDMAdapter,
    "taobao": TaobaoAdapter,
    "pdd": PddAdapter,
    "redbook": RedBookAdapter,
}


def _print_report(report) -> None:
    if hasattr(report, "model_dump"):
        data = report.model_dump()
    else:
        data = report.dict()
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print("\nNext steps:")
    print("  python scripts/analyze_comments.py")
    print("  python scripts/calculate_scores.py")


def main() -> int:
    parser = argparse.ArgumentParser(description="Import real/manual CampRank data.")
    parser.add_argument("--json", dest="json_path")
    parser.add_argument("--csv-folder", dest="csv_folder")
    parser.add_argument("--adapter", choices=sorted(ADAPTERS))
    parser.add_argument("--input", dest="input_path")
    parser.add_argument("--source-name", default=None)
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_sample_data(db)
        if args.json_path:
            report = import_from_json(db, args.json_path, source_name=args.source_name or "manual_json")
        elif args.csv_folder:
            report = import_from_csv_folder(db, args.csv_folder, source_name=args.source_name or "manual_csv")
        elif args.adapter:
            adapter = ADAPTERS[args.adapter](args.input_path)
            raw_data = adapter.fetch_raw_data(keyword="")
            normalized = adapter.normalize(raw_data)
            report = adapter.import_to_db(db, normalized)
        else:
            parser.error("Provide --json, --csv-folder, or --adapter with --input.")
        _print_report(report)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

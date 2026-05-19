from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models import *  # noqa: F401,F403,E402
from app.services.comment_analysis_service import (  # noqa: E402
    analyze_and_update_comments,
    analyze_and_update_redbook_notes,
)
from app.services.sample_data_service import ensure_sample_data  # noqa: E402


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_sample_data(db)
        comment_summary = analyze_and_update_comments(db)
        redbook_summary = analyze_and_update_redbook_notes(db)
        print("CampRank comment analysis completed.")
        print(f"Comments analyzed: {comment_summary['comment_count']}")
        print(f"Comment quality rows: {comment_summary['quality_analysis_count']}")
        print(f"Negative analysis rows: {comment_summary['negative_analysis_count']}")
        print(f"RedBook notes analyzed: {redbook_summary['note_count']}")
    finally:
        db.close()


if __name__ == "__main__":
    main()


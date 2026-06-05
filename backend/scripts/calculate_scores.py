from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.config import get_settings  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models import *  # noqa: F401,F403,E402
from app.models.product import CanonicalProduct  # noqa: E402
from app.services.comment_analysis_service import analyze_and_update_comments, analyze_and_update_redbook_notes  # noqa: E402
from app.services.sample_data_service import ensure_sample_data  # noqa: E402
from app.services.scoring_service import calculate_all_scores  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze comments and calculate scores.")
    parser.add_argument("--no-sample-data", action="store_true", help="Do not seed sample/mock data when the database is empty.")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_sample_data = get_settings().sample_data_enabled and not args.no_sample_data
        if seed_sample_data and db.query(CanonicalProduct.id).first() is None:
            ensure_sample_data(db)
        comment_result = analyze_and_update_comments(db)
        redbook_result = analyze_and_update_redbook_notes(db)
        score_result = calculate_all_scores(db, seed_sample_data=seed_sample_data)
        print(f"updated comments: {comment_result['comment_count']}")
        print(f"updated redbook notes: {redbook_result['note_count']}")
        print(f"updated platform offers: {score_result['updated_platform_offers']}")
        print(f"updated product scores: {score_result['updated_product_scores']}")
    finally:
        db.close()


if __name__ == "__main__":
    main()

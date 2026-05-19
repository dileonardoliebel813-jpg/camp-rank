from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.database import SessionLocal  # noqa: E402
from app.services.sample_data_service import ensure_sample_data  # noqa: E402


def main() -> None:
    db = SessionLocal()
    try:
        ensure_sample_data(db)
        print("CampRank sample data seeded.")
    finally:
        db.close()


if __name__ == "__main__":
    main()

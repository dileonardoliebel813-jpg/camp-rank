from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.database import Base, engine  # noqa: E402
from app.models import *  # noqa: F401,F403,E402


def main() -> None:
    Base.metadata.create_all(bind=engine)
    print("CampRank database tables created.")


if __name__ == "__main__":
    main()

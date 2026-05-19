# CampRank Backend

FastAPI + SQLAlchemy + SQLite skeleton for Agent 2.

## Setup

```bash
pip install -r requirements.txt
python scripts/init_db.py
python scripts/seed_sample_data.py
uvicorn app.main:app --reload
```

## Tests

```bash
python -m pytest
```

# CampRank Backend

FastAPI backend for product ingestion, scoring, recommendation ranking, product detail, and price comparison APIs.

## Run

```bash
pip install -r requirements.txt
python scripts/init_db.py
python scripts/seed_sample_data.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Test

```bash
python -m pytest
```

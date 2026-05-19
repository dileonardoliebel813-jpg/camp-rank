import json
from pathlib import Path

from app.models.product import Product


class FakeJDPublicCommentFetcher:
    def __init__(self):
        self.warnings = []
        self.errors = []

    def fetch_comments(self, sku_id, max_pages=3, page_size=10, delay_seconds=2.0):
        return {
            "comments": [{"platform": "JD", "comment_text": "api mock comment", "rating": 5}],
            "warnings": [],
            "errors": [],
        }

    def save_comments_json(self, sku_id, comments):
        return str(Path(__file__).resolve().parents[1] / "data" / "real_samples" / f"jd_comments_{sku_id}.json")


def test_jd_comments_fetch_api_returns_200(client, monkeypatch):
    monkeypatch.setattr("app.api.ingestion.JDPublicCommentFetcher", FakeJDPublicCommentFetcher)

    response = client.post(
        "/api/ingestion/jd-comments/fetch",
        json={"sku_id": "100000000000", "max_pages": 3, "page_size": 10, "save_only": True},
    )

    assert response.status_code == 200
    assert response.json()["fetched_count"] == 1
    assert response.json()["saved_json_path"].endswith("jd_comments_100000000000.json")


def test_jd_comments_import_api_returns_200(client, db_session):
    product = db_session.query(Product).filter(Product.platform == "JD").first()
    path = Path(__file__).resolve().parents[1] / "data" / "real_samples" / f"jd_comments_{product.platform_product_id}.json"
    path.write_text(
        json.dumps(
            {
                "source_name": "jd_public_comment",
                "platform": "JD",
                "sku_id": product.platform_product_id,
                "fetched_at": "2026-05-01T00:00:00+00:00",
                "max_pages": 1,
                "comments": [{"platform": "JD", "comment_text": "api import comment", "rating": 5}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    try:
        response = client.post(
            "/api/ingestion/jd-comments/import",
            json={"path": f"backend/data/real_samples/{path.name}"},
        )
    finally:
        path.unlink(missing_ok=True)

    assert response.status_code == 200
    assert response.json()["imported_comments"] == 1


def test_jd_comments_import_api_rejects_non_real_samples_path(client):
    response = client.post("/api/ingestion/jd-comments/import", json={"path": "README.md"})

    assert response.status_code == 400

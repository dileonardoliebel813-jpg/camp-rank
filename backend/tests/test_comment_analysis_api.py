from app.models import CanonicalProduct


COMMENT_SUMMARY_FIELDS = {
    "waterproof_negative_rate",
    "windproof_negative_rate",
    "space_negative_rate",
    "storage_negative_rate",
    "setup_negative_rate",
    "smell_negative_rate",
    "sunproof_negative_rate",
    "return_after_sale_negative_rate",
    "high_risk_tags",
    "suspected_fake_review_count",
    "low_information_review_count",
    "valid_negative_review_count",
}

REDBOOK_SUMMARY_FIELDS = {
    "note_count",
    "suspected_ad_count",
    "average_credibility_score",
    "average_sentiment_score",
    "risk_tags",
}


def test_comment_risk_summary_api_returns_fields(client, db_session):
    canonical = db_session.query(CanonicalProduct).first()

    response = client.get(f"/api/products/{canonical.id}/comment-risk-summary")

    assert response.status_code == 200
    assert COMMENT_SUMMARY_FIELDS.issubset(response.json().keys())


def test_redbook_summary_api_returns_fields(client, db_session):
    canonical = db_session.query(CanonicalProduct).first()

    response = client.get(f"/api/products/{canonical.id}/redbook-summary")

    assert response.status_code == 200
    assert REDBOOK_SUMMARY_FIELDS.issubset(response.json().keys())


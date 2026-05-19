from app.models import CanonicalProduct


def test_price_compare_api_returns_required_fields(client, db_session):
    canonical = db_session.query(CanonicalProduct).first()
    response = client.get(f"/api/price-compare/{canonical.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["offers"]
    assert data["lowest_price_platform"]
    assert data["recommended_platform"]
    assert "price_gap" in data
    assert "explanation" in data
    assert {"platform", "stable_final_price", "risk_adjusted_cost", "warning_tags"}.issubset(
        data["offers"][0].keys()
    )


def test_recommended_platform_can_differ_from_lowest_price(client, db_session):
    canonical_products = db_session.query(CanonicalProduct).all()

    comparisons = [client.get(f"/api/price-compare/{canonical.id}").json() for canonical in canonical_products]

    assert any(
        comparison["recommended_platform"] != comparison["lowest_price_platform"]
        for comparison in comparisons
    )

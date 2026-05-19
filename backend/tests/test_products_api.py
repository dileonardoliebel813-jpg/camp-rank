from app.models import CanonicalProduct


def test_products_api_returns_products(client):
    response = client.get("/api/products")

    assert response.status_code == 200
    data = response.json()
    assert data
    assert {"recommended_platform", "lowest_price_platform", "main_risk_tags"}.issubset(data[0].keys())


def test_product_detail_api_returns_full_detail(client, db_session):
    canonical = db_session.query(CanonicalProduct).first()
    response = client.get(f"/api/products/{canonical.id}")

    assert response.status_code == 200
    data = response.json()
    required_keys = {
        "canonical_product",
        "products",
        "specs",
        "prices",
        "benefits",
        "return_policy",
        "comments",
        "comment_quality_analysis",
        "negative_review_analysis",
        "redbook_notes",
        "platform_offer_analysis",
        "product_score",
    }
    assert required_keys.issubset(data.keys())
    assert len(data["products"]) >= 2


def test_products_api_filters_work(client):
    brand_response = client.get("/api/products", params={"brand": "北岭"})
    use_case_response = client.get("/api/products", params={"use_case": "过夜轻露营"})
    price_response = client.get("/api/products", params={"min_price": 100, "max_price": 700})
    platform_response = client.get("/api/products", params={"platform": "JD"})

    assert brand_response.status_code == 200
    assert all(item["brand"] == "北岭" for item in brand_response.json())
    assert use_case_response.status_code == 200
    assert all(item["use_case"] == "过夜轻露营" for item in use_case_response.json())
    assert price_response.status_code == 200
    assert price_response.json()
    assert platform_response.status_code == 200
    assert platform_response.json()

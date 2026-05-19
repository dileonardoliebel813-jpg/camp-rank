def test_recommendations_api_returns_200(client):
    response = client.get("/api/recommendations")
    assert response.status_code == 200
    assert response.json()


def test_recommendations_api_supports_price_filters(client):
    response = client.get("/api/recommendations", params={"min_price": 100, "max_price": 900})
    assert response.status_code == 200
    assert all(100 <= item["stable_final_price"] <= 900 for item in response.json())


def test_recommendations_api_supports_scenario_and_preference(client):
    response = client.get(
        "/api/recommendations",
        params={"scenario": "after_sale", "preference": "after_sale", "limit": 5},
    )
    assert response.status_code == 200
    assert len(response.json()) <= 5


def test_recommendations_api_returns_platform_fields(client):
    response = client.get("/api/recommendations")
    item = response.json()[0]
    assert item["recommended_platform"]
    assert item["lowest_price_platform"]
    assert "recommended_after_sale_service" in item


def test_recommendations_api_returns_strict_selection_fields(client):
    response = client.get(
        "/api/recommendations",
        params={"scenario": "rain_backup", "preference": "weather_protection", "limit": 5},
    )
    assert response.status_code == 200
    item = response.json()[0]
    assert item["selection_tier"] in {"core_match", "partial_match", "fallback"}
    assert "strict_match_score" in item
    assert isinstance(item["matched_requirements"], list)
    assert isinstance(item["unmet_requirements"], list)
    assert "selection_summary" in item


def test_recommendations_api_has_sample_where_recommended_differs_from_lowest(client):
    response = client.get("/api/recommendations", params={"limit": 20})
    assert response.status_code == 200
    assert any(
        item["recommended_platform"] != item["lowest_price_platform"]
        for item in response.json()
    )

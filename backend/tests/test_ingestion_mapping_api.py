def test_platform_mapping_api_returns_200(client):
    response = client.get("/api/ingestion/platform-mapping")
    assert response.status_code == 200
    data = response.json()
    assert "JD" in data["platforms"]
    assert "SMZDM" in data["platforms"]


def test_quality_report_api_returns_200(client):
    response = client.get("/api/ingestion/quality-report")
    assert response.status_code == 200
    assert response.json()["status"] in {"empty", "ok"}

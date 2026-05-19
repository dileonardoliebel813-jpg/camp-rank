def test_import_json_api_allows_real_samples_path(client):
    response = client.post(
        "/api/ingestion/import-json",
        json={"path": "backend/data/real_samples/tents_real_sample.json", "source_name": "api_test"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["source_name"] == "api_test"
    assert "imported_platform_products" in data


def test_import_json_api_rejects_path_outside_real_samples(client):
    response = client.post(
        "/api/ingestion/import-json",
        json={"path": "README.md", "source_name": "api_test"},
    )
    assert response.status_code == 400


def test_import_status_api_returns_200(client):
    response = client.get("/api/ingestion/import-status")
    assert response.status_code == 200
    assert response.json()["status"] in {"empty", "ok"}


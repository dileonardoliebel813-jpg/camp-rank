def test_fetch_official_api_defaults_to_dry_run(client, monkeypatch):
    monkeypatch.setenv("JD_API_ENABLED", "false")
    response = client.post(
        "/api/ingestion/fetch-official",
        json={"source": "jd", "keyword": "帐篷", "limit": 5, "live": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "jd"
    assert data["source_type"] == "official_api"
    assert data["dry_run"] is True
    assert data["imported_count"] == 0
    assert data["errors"]
    assert "JD_API_ENABLED=false" in data["errors"][0]


def test_fetch_official_api_does_not_return_secrets(client, monkeypatch):
    monkeypatch.setenv("TAOBAO_APP_SECRET", "hidden-secret")
    response = client.post(
        "/api/ingestion/fetch-official",
        json={"source": "taobao", "keyword": "帐篷", "limit": 5, "live": True, "dry_run": True},
    )
    assert response.status_code == 200
    assert "hidden-secret" not in response.text

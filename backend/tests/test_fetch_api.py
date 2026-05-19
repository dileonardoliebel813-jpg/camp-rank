def test_fetch_real_api_local_input_returns_200(client):
    response = client.post(
        "/api/ingestion/fetch-real",
        json={
            "source": "smzdm",
            "keyword": "帐篷",
            "limit": 20,
            "live": False,
            "input_path": "backend/data/real_samples/smzdm_tents_sample.json",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "smzdm"
    assert data["live_mode"] is False
    assert not data["errors"]


def test_fetch_real_api_rejects_non_real_samples_path(client):
    response = client.post(
        "/api/ingestion/fetch-real",
        json={
            "source": "smzdm",
            "keyword": "帐篷",
            "limit": 20,
            "live": False,
            "input_path": "README.md",
        },
    )
    assert response.status_code == 400


def test_fetch_status_api_returns_200(client):
    response = client.get("/api/ingestion/fetch-status")
    assert response.status_code == 200
    assert response.json()["status"] in {"empty", "ok"}

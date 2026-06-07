from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.services.deepseek_client import DeepSeekClientError


def _chat_payload(text="need a tent, budget 900, waterproof"):
    return {
        "messages": [{"role": "user", "content": text}],
        "intent_state": {},
        "current_filters": {},
    }


def _complete_slots(**overrides):
    slots = {
        "min_price": 0,
        "max_price": 900,
        "scenario": "rain_backup",
        "preferences": ["weather_protection"],
        "people_count": 2,
        "weather_or_setup_concern": "weather_protection",
        "risk_tolerance": "balanced",
    }
    slots.update(overrides)
    return slots


def test_chat_recommendation_returns_ready_after_fifth_confirmed_step(client, monkeypatch):
    def fake_extract(*_args):
        return {
            "action": "recommend",
            "assistant_message": "ready",
            "slots": {"risk_tolerance": "balanced"},
            "missing_fields": [],
        }

    monkeypatch.setattr("app.services.chat_intent_service.extract_intent_with_llm", fake_extract)

    response = client.post(
        "/api/chat/recommendation",
        json={
            "messages": [{"role": "user", "content": "final answer: safer choice"}],
            "intent_state": {
                "min_price": 0,
                "max_price": 900,
                "scenario": "rain_backup",
                "preferences": ["weather_protection"],
                "people_count": 2,
                "weather_or_setup_concern": "weather_protection",
                "confirmed_fields": ["budget", "scenario", "people_count", "weather_or_setup_concern"],
                "conversation_step": 4,
                "pending_question_field": "risk_tolerance",
            },
            "current_filters": {},
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["filters"]["max_price"] == 900
    assert data["filters"]["scenario"] == "rain_backup"
    assert data["filters"]["preference"] == "weather_protection"
    assert data["intent_state"]["conversation_step"] == 5
    assert data["intent_state"]["confirmed_fields"] == [
        "budget",
        "scenario",
        "people_count",
        "weather_or_setup_concern",
        "risk_tolerance",
    ]
    assert data["question_field"] is None
    assert data["quick_replies"] == []
    assert data["recommendations"]
    assert "product_name" in data["recommendations"][0]


def test_chat_recommendation_clarifies_incomplete_budget(client, monkeypatch):
    def fake_extract(*_args):
        return {
            "action": "clarify",
            "assistant_message": "need budget",
            "slots": _complete_slots(max_price=None),
            "missing_fields": ["budget"],
        }

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("recommendation flow should not run while intent is incomplete")

    monkeypatch.setattr("app.services.chat_intent_service.extract_intent_with_llm", fake_extract)
    monkeypatch.setattr("app.services.chat_intent_service.build_recommendation_response", fail_if_called)

    response = client.post("/api/chat/recommendation", json=_chat_payload("need a tent"))

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "needs_clarification"
    assert data["missing_fields"][0] == "budget"
    assert data["question_field"] == "budget"
    assert data["quick_replies"]
    assert data["recommendations"] == []


def test_chat_recommendation_asks_scenario_after_budget_known(client, monkeypatch):
    def fake_extract(*_args):
        return {
            "action": "clarify",
            "assistant_message": "need scenario",
            "slots": _complete_slots(scenario=None),
            "missing_fields": ["scenario"],
        }

    monkeypatch.setattr("app.services.chat_intent_service.extract_intent_with_llm", fake_extract)

    response = client.post("/api/chat/recommendation", json=_chat_payload("budget 500 waterproof"))

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "needs_clarification"
    assert data["question_field"] == "scenario"
    assert any(reply["message"] for reply in data["quick_replies"])


def test_chat_recommendation_asks_people_count_as_third_step(client, monkeypatch):
    def fake_extract(*_args):
        return {
            "action": "clarify",
            "assistant_message": "need people count",
            "slots": _complete_slots(people_count=None),
            "missing_fields": ["people_count"],
        }

    monkeypatch.setattr("app.services.chat_intent_service.extract_intent_with_llm", fake_extract)

    response = client.post(
        "/api/chat/recommendation",
        json={
            "messages": [{"role": "user", "content": "weekend park"}],
            "intent_state": {
                "min_price": 0,
                "max_price": 500,
                "confirmed_fields": ["budget"],
                "conversation_step": 1,
                "pending_question_field": "scenario",
            },
            "current_filters": {},
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "needs_clarification"
    assert data["question_field"] == "people_count"
    assert len(data["quick_replies"]) >= 3


def test_chat_recommendation_asks_concern_as_fourth_step(client, monkeypatch):
    def fake_extract(*_args):
        return {
            "action": "clarify",
            "assistant_message": "need concern",
            "slots": _complete_slots(weather_or_setup_concern=None, preferences=[]),
            "missing_fields": ["weather_or_setup_concern"],
        }

    monkeypatch.setattr("app.services.chat_intent_service.extract_intent_with_llm", fake_extract)

    response = client.post(
        "/api/chat/recommendation",
        json={
            "messages": [{"role": "user", "content": "2 people"}],
            "intent_state": {
                "min_price": 0,
                "max_price": 500,
                "scenario": "newbie_weekend",
                "confirmed_fields": ["budget", "scenario"],
                "conversation_step": 2,
                "pending_question_field": "people_count",
            },
            "current_filters": {},
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "needs_clarification"
    assert data["question_field"] == "weather_or_setup_concern"
    assert len(data["quick_replies"]) >= 3


def test_chat_recommendation_asks_risk_tolerance_as_fifth_step(client, monkeypatch):
    def fake_extract(*_args):
        return {
            "action": "clarify",
            "assistant_message": "need risk tolerance",
            "slots": _complete_slots(risk_tolerance=None),
            "missing_fields": ["risk_tolerance"],
        }

    monkeypatch.setattr("app.services.chat_intent_service.extract_intent_with_llm", fake_extract)

    response = client.post(
        "/api/chat/recommendation",
        json={
            "messages": [{"role": "user", "content": "waterproof"}],
            "intent_state": {
                "min_price": 0,
                "max_price": 500,
                "scenario": "newbie_weekend",
                "people_count": 2,
                "confirmed_fields": ["budget", "scenario", "people_count"],
                "conversation_step": 3,
                "pending_question_field": "weather_or_setup_concern",
            },
            "current_filters": {},
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "needs_clarification"
    assert data["question_field"] == "risk_tolerance"
    assert len(data["quick_replies"]) >= 3


def test_chat_recommendation_fifth_step_completion_can_return_ready(client, monkeypatch):
    def fake_extract(*_args):
        return {
            "action": "clarify",
            "assistant_message": "old clarify text should not block ready",
            "slots": {"risk_tolerance": "balanced"},
            "missing_fields": [],
        }

    monkeypatch.setattr("app.services.chat_intent_service.extract_intent_with_llm", fake_extract)

    response = client.post(
        "/api/chat/recommendation",
        json={
            "messages": [{"role": "user", "content": "final answer: safer choice"}],
            "intent_state": {
                "min_price": 0,
                "max_price": 500,
                "scenario": "newbie_weekend",
                "people_count": 2,
                "weather_or_setup_concern": "weather_protection",
                "preferences": ["weather_protection"],
                "confirmed_fields": ["budget", "scenario", "people_count", "weather_or_setup_concern"],
                "conversation_step": 4,
                "pending_question_field": "risk_tolerance",
            },
            "current_filters": {},
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["filters"]["scenario"] == "newbie_weekend"
    assert data["filters"]["preference"] == "weather_protection"
    assert data["recommendations"]


def test_chat_recommendation_runs_five_step_flow_with_local_fallback(client, monkeypatch):
    def fake_extract(*_args):
        raise DeepSeekClientError("llm_api_timeout", "timeout")

    monkeypatch.setattr("app.services.chat_intent_service.extract_intent_with_llm", fake_extract)

    state = {}

    def send(text):
        response = client.post(
            "/api/chat/recommendation",
            json={
                "messages": [{"role": "user", "content": text}],
                "intent_state": state,
                "current_filters": {},
            },
        )
        assert response.status_code == 200
        return response.json()

    data = send("预算500")
    state = data["intent_state"]
    assert data["status"] == "needs_clarification"
    assert data["question_field"] == "scenario"
    assert state["conversation_step"] == 1

    data = send("使用场景是周末公园或新手露营")
    state = data["intent_state"]
    assert data["status"] == "needs_clarification"
    assert data["question_field"] == "people_count"
    assert state["conversation_step"] == 2

    data = send("大概1到2个人使用，够用就行")
    state = data["intent_state"]
    assert data["status"] == "needs_clarification"
    assert data["question_field"] == "weather_or_setup_concern"
    assert state["conversation_step"] == 3

    data = send("最担心防水防风问题")
    state = data["intent_state"]
    assert data["status"] == "needs_clarification"
    assert data["question_field"] == "risk_tolerance"
    assert state["conversation_step"] == 4

    data = send("最后我更想要稳妥推荐，不想踩坑")
    assert data["status"] == "ready"
    assert data["intent_state"]["conversation_step"] == 5
    assert data["intent_state"]["confirmed_fields"] == [
        "budget",
        "scenario",
        "people_count",
        "weather_or_setup_concern",
        "risk_tolerance",
    ]
    assert data["recommendations"]


def test_chat_recommendation_incomplete_llm_response_falls_back_to_clarification(client, monkeypatch):
    monkeypatch.setattr("app.services.chat_intent_service.extract_intent_with_llm", lambda *_args: {"action": "recommend"})

    response = client.post("/api/chat/recommendation", json=_chat_payload())

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "needs_clarification"
    assert data["question_field"] == "scenario"
    assert data["recommendations"] == []


def test_chat_recommendation_complete_first_turn_still_requires_confirmations(client, monkeypatch):
    def fake_extract(*_args):
        return {
            "action": "recommend",
            "assistant_message": "should not recommend yet",
            "slots": _complete_slots(),
            "missing_fields": [],
        }

    monkeypatch.setattr("app.services.chat_intent_service.extract_intent_with_llm", fake_extract)

    response = client.post(
        "/api/chat/recommendation",
        json=_chat_payload("budget 500, two people, weekend park, waterproof, easy setup, safer choice"),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "needs_clarification"
    assert data["question_field"] == "scenario"
    assert data["intent_state"]["confirmed_fields"] == ["budget"]
    assert data["recommendations"] == []


def test_chat_recommendation_reports_llm_api_key_missing(client, monkeypatch):
    def fake_extract(*_args):
        raise DeepSeekClientError("llm_api_key_missing", "DeepSeek API key is not configured.")

    monkeypatch.setattr("app.services.chat_intent_service.extract_intent_with_llm", fake_extract)

    response = client.post(
        "/api/chat/recommendation",
        json={
            "messages": [{"role": "user", "content": "final answer: safer choice"}],
            "intent_state": {
                "min_price": 0,
                "max_price": 1,
                "scenario": "rain_backup",
                "preferences": ["weather_protection"],
                "people_count": 2,
                "weather_or_setup_concern": "weather_protection",
                "confirmed_fields": ["budget", "scenario", "people_count", "weather_or_setup_concern"],
                "conversation_step": 4,
                "pending_question_field": "risk_tolerance",
            },
            "current_filters": {},
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"]["error_code"] == "llm_api_key_missing"


def test_chat_recommendation_reports_empty_database(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'empty_chat.db'}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    monkeypatch.setattr("app.services.chat_intent_service.extract_intent_with_llm", lambda *_args: {})
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            response = test_client.post("/api/chat/recommendation", json=_chat_payload())
    finally:
        app.dependency_overrides.clear()
        db.close()

    assert response.status_code == 503
    assert response.json()["detail"]["error_code"] == "recommendation_data_empty"


def test_chat_recommendation_reports_empty_recommendation_result(client, monkeypatch):
    def fake_extract(*_args):
        return {
            "action": "recommend",
            "assistant_message": "recommend",
            "slots": _complete_slots(max_price=1),
            "missing_fields": [],
        }

    monkeypatch.setattr("app.services.chat_intent_service.extract_intent_with_llm", fake_extract)
    monkeypatch.setattr("app.services.chat_intent_service.build_recommendation_response", lambda _db, _filters: [])

    response = client.post(
        "/api/chat/recommendation",
        json={
            "messages": [{"role": "user", "content": "final answer: safer choice"}],
            "intent_state": {
                "min_price": 0,
                "max_price": 1,
                "scenario": "rain_backup",
                "preferences": ["weather_protection"],
                "people_count": 2,
                "weather_or_setup_concern": "weather_protection",
                "confirmed_fields": ["budget", "scenario", "people_count", "weather_or_setup_concern"],
                "conversation_step": 4,
                "pending_question_field": "risk_tolerance",
            },
            "current_filters": {},
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"]["error_code"] == "recommendation_data_empty"

import re
from dataclasses import dataclass

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.models import CanonicalProduct
from app.schemas.chat import ChatRecommendationRequest
from app.services.deepseek_client import DeepSeekClientError, request_chat_json
from app.services.scoring_service import build_recommendation_response


SCENARIO_OPTIONS = {
    "newbie_weekend": "short weekend park or casual beginner camping",
    "family_camping": "family or parent-child camping",
    "overnight": "short overnight camping",
    "rain_backup": "rainy, humid, waterproof backup scenario",
    "group_party": "group gathering or large space scenario",
    "hiking_lightweight": "walking or hiking with portability pressure",
}

SCENARIO_ANSWERS = {
    "newbie_weekend": "weekend_park",
    "family_camping": "family",
    "overnight": "overnight",
    "rain_backup": "rain",
    "group_party": "group",
    "hiking_lightweight": "carry_light",
}

PREFERENCE_OPTIONS = {
    "balanced": "balanced risk control",
    "lowest_price": "lowest stable final price",
    "after_sale": "return, refund, and after-sale protection",
    "gift_package": "capacity and space",
    "portable": "storage, weight, and carrying burden",
    "weather_protection": "waterproof and windproof feedback",
    "easy_setup": "easy or fast setup",
    "less_stuffy": "less stuffy, smell, or ventilation concern",
}

PREFERENCE_TO_CONCERN = {
    "balanced": "risk_control",
    "lowest_price": "price_priority",
    "after_sale": "after_sale",
    "gift_package": "space",
    "portable": "portable",
    "weather_protection": "weather",
    "easy_setup": "easy_setup",
    "less_stuffy": "less_stuffy",
}

REQUIRED_QUESTION_FLOW = ["budget", "scenario", "people_count", "weather_or_setup_concern", "risk_tolerance"]
REQUIRED_FIELDS = set(REQUIRED_QUESTION_FLOW)
CONCERN_OPTIONS = {"weather_protection", "easy_setup", "portable", "after_sale", "less_stuffy"}
RISK_TOLERANCE_OPTIONS = {"balanced", "lowest_price", "after_sale", "accept_risk"}


QUICK_REPLY_OPTIONS = {
    "budget": [
        {"label": "300以内", "message": "预算300以内"},
        {"label": "500以内", "message": "预算500以内"},
        {"label": "800以内", "message": "预算800以内"},
    ],
    "scenario": [
        {"label": "周末公园/新手露营", "message": "使用场景是周末公园或新手露营"},
        {"label": "家庭亲子", "message": "使用场景是家庭亲子露营"},
        {"label": "短途过夜", "message": "使用场景是短途过夜露营"},
        {"label": "雨天潮湿", "message": "使用场景是雨天或潮湿环境"},
        {"label": "多人大空间", "message": "使用场景是多人聚会或需要大空间"},
        {"label": "步行携带", "message": "使用场景是步行携带或徒步"},
    ],
    "people_count": [
        {"label": "1-2人够用", "message": "大概1到2个人使用，够用就行"},
        {"label": "3-4人", "message": "大概3到4个人使用，希望空间舒服一点"},
        {"label": "多人/大空间", "message": "多人使用，更在意空间容量"},
    ],
    "weather_or_setup_concern": [
        {"label": "防水防风", "message": "最担心防水防风问题"},
        {"label": "好搭建", "message": "最担心搭建复杂，想要好搭建"},
        {"label": "收纳便携", "message": "最担心收纳和携带负担"},
        {"label": "售后退换", "message": "最担心售后退换问题"},
        {"label": "闷热/异味", "message": "最担心闷热和异味反馈"},
    ],
    "risk_tolerance": [
        {"label": "稳妥推荐", "message": "最后我更想要稳妥推荐，不想踩坑"},
        {"label": "低价优先", "message": "最后我更想要低价优先"},
        {"label": "售后安心", "message": "最后我更想要售后安心"},
        {"label": "能接受风险", "message": "最后我能接受一点风险换价格"},
    ],
    "preference": [
        {"label": "综合稳妥", "message": "最在意综合稳妥"},
        {"label": "到手价优先", "message": "最在意到手价优先"},
        {"label": "售后退换", "message": "最在意售后退换"},
        {"label": "防水防风", "message": "最在意防水防风"},
        {"label": "空间容量", "message": "最在意空间容量"},
        {"label": "收纳便携", "message": "最在意收纳便携"},
        {"label": "好搭建", "message": "最在意好搭建"},
        {"label": "透气/异味", "message": "最在意透气和异味反馈"},
    ],
}


@dataclass
class ChatServiceError(Exception):
    code: str
    message: str
    status_code: int = 500


def _safe_number(value):
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def _safe_int(value, default: int = 0) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _clean_confirmed_fields(value) -> list[str]:
    fields = []
    for raw in value or []:
        item = str(raw).strip()
        if item in REQUIRED_FIELDS and item not in fields:
            fields.append(item)
    return [field for field in REQUIRED_QUESTION_FLOW if field in fields]


def _clean_preferences(value) -> list[str]:
    if value is None:
        return []
    raw_values = value if isinstance(value, list) else str(value).split(",")
    preferences = []
    for raw in raw_values:
        item = str(raw).strip()
        if item in PREFERENCE_OPTIONS and item not in preferences:
            preferences.append(item)
    if len(preferences) > 1 and "balanced" in preferences:
        preferences = [item for item in preferences if item != "balanced"]
    return preferences


def _normalize_state(raw_state: dict | None) -> dict:
    raw_state = raw_state or {}
    preferences = _clean_preferences(raw_state.get("preferences") or raw_state.get("preference"))
    scenario = raw_state.get("scenario")
    concern = str(raw_state.get("weather_or_setup_concern") or "").strip()
    risk_tolerance = str(raw_state.get("risk_tolerance") or "").strip()
    pending_question_field = str(raw_state.get("pending_question_field") or "").strip()
    confirmed_fields = _clean_confirmed_fields(raw_state.get("confirmed_fields"))
    return {
        "min_price": _safe_number(raw_state.get("min_price")),
        "max_price": _safe_number(raw_state.get("max_price")),
        "scenario": scenario if scenario in SCENARIO_OPTIONS else None,
        "preferences": preferences,
        "people_count": _safe_number(raw_state.get("people_count")),
        "weather_or_setup_concern": concern if concern in CONCERN_OPTIONS else None,
        "risk_tolerance": risk_tolerance if risk_tolerance in RISK_TOLERANCE_OPTIONS else None,
        "confirmed_fields": confirmed_fields,
        "conversation_step": _safe_int(raw_state.get("conversation_step"), len(confirmed_fields)),
        "pending_question_field": pending_question_field if pending_question_field in REQUIRED_FIELDS else None,
        "unsupported_notes": list(raw_state.get("unsupported_notes") or []),
    }


def _state_from_filters(raw_filters: dict | None) -> dict:
    raw_filters = raw_filters or {}
    preferences = _clean_preferences(raw_filters.get("preference"))
    scenario = raw_filters.get("scenario")
    return {
        "min_price": _safe_number(raw_filters.get("min_price")),
        "max_price": _safe_number(raw_filters.get("max_price")),
        "scenario": scenario if scenario in SCENARIO_OPTIONS else None,
        "preferences": preferences,
    }


def _latest_user_text(request: ChatRecommendationRequest) -> str:
    texts = [
        str(message.content or "")
        for message in request.messages
        if message.role == "user" and str(message.content or "").strip()
    ]
    return "\n".join(texts[-4:])


def _heuristic_state_from_text(text: str) -> dict:
    text = text or ""
    state = {
        "min_price": None,
        "max_price": None,
        "scenario": None,
        "preferences": [],
        "people_count": None,
        "weather_or_setup_concern": None,
        "risk_tolerance": None,
        "unsupported_notes": [],
    }

    # Keep this fallback language-agnostic so Windows console encoding cannot
    # break obvious budget extraction. Ignore small counts such as "3 people".
    numbers = [
        float(match.group(0))
        for match in re.finditer(r"\d+(?:\.\d+)?", text)
    ]
    budget_candidates = [number for number in numbers if 50 <= number <= 10000]
    if budget_candidates:
        state["max_price"] = budget_candidates[0]
        state["min_price"] = 0

    people_match = re.search(
        r"(\d+)(?:\s*(?:\u5230|-|~|\u81f3)\s*(\d+))?\s*(?:\u4e2a)?\s*(?:\u4eba|people|person)",
        text,
        re.IGNORECASE,
    )
    if people_match:
        state["people_count"] = _safe_number(people_match.group(2) or people_match.group(1))
    if state["people_count"] is None:
        chinese_people = {
            "\u4e00": 1,
            "\u4e8c": 2,
            "\u4e24": 2,
            "\u4e09": 3,
            "\u56db": 4,
            "\u4e94": 5,
            "\u516d": 6,
            "\u4e03": 7,
            "\u516b": 8,
            "\u4e5d": 9,
            "\u5341": 10,
        }
        chinese_people_match = re.search(r"([\u4e00\u4e8c\u4e24\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341])\s*(?:\u4e2a)?\s*\u4eba", text)
        if chinese_people_match:
            state["people_count"] = chinese_people.get(chinese_people_match.group(1))
    if state["people_count"] is None and any(keyword in text for keyword in ("\u591a\u4eba", "\u5927\u7a7a\u95f4", "\u805a\u4f1a", "\u56e2\u5efa")):
        state["people_count"] = 4

    if any(keyword in text for keyword in ("\u84dd\u8272", "\u7ea2\u8272", "\u9ed1\u8272", "\u767d\u8272", "\u7eff\u8272", "\u989c\u8272")):
        state["unsupported_notes"].append("color")

    scenario_rules = [
        ("rain_backup", ("\u96e8\u5929", "\u4e0b\u96e8", "\u6f6e\u6e7f")),
        ("overnight", ("\u8fc7\u591c", "\u591c\u5bbf", "\u4f4f\u4e00\u665a", "\u7761\u89c9")),
        ("group_party", ("\u591a\u4eba", "\u805a\u4f1a", "\u5927\u7a7a\u95f4", "\u56e2\u5efa")),
        ("family_camping", ("\u5bb6\u5ead", "\u4eb2\u5b50", "\u5b69\u5b50", "\u4e00\u5bb6")),
        ("hiking_lightweight", ("\u5f92\u6b65", "\u80cc\u5305", "\u8f7b\u91cf", "\u8f7b\u4fbf", "\u643a\u5e26", "\u6536\u7eb3")),
        ("newbie_weekend", ("\u6237\u5916", "\u91ce\u8425", "\u516c\u56ed", "\u5468\u672b", "\u65b0\u624b")),
    ]
    for scenario, keywords in scenario_rules:
        if any(keyword in text for keyword in keywords):
            state["scenario"] = scenario
            break

    preference_rules = [
        ("lowest_price", ("\u4fbf\u5b9c", "\u4f4e\u4ef7", "\u6027\u4ef7\u6bd4", "\u7701\u94b1")),
        ("after_sale", ("\u552e\u540e", "\u9000\u8d27", "\u9000\u6b3e", "\u9000\u6362")),
        ("gift_package", ("\u7a7a\u95f4", "3\u4eba", "\u4e09\u4eba", "4\u4eba", "\u56db\u4eba", "\u5bb9\u91cf")),
        ("portable", ("\u8f7b\u4fbf", "\u4fbf\u643a", "\u6536\u7eb3", "\u643a\u5e26", "\u5f92\u6b65")),
        ("weather_protection", ("\u9632\u6c34", "\u9632\u98ce", "\u6f0f\u6c34", "\u96e8")),
        ("easy_setup", ("\u597d\u642d", "\u6613\u642d", "\u901f\u5f00", "\u81ea\u52a8", "\u642d\u5efa")),
        ("less_stuffy", ("\u95f7", "\u5f02\u5473", "\u900f\u6c14", "\u901a\u98ce")),
        ("balanced", ("\u968f\u4fbf", "\u90fd\u53ef\u4ee5", "\u90fd\u884c", "\u7efc\u5408", "\u7a33\u59a5")),
    ]
    for preference, keywords in preference_rules:
        if any(keyword in text for keyword in keywords):
            state["preferences"].append(preference)

    concern_rules = [
        ("weather_protection", ("\u9632\u6c34", "\u9632\u98ce", "\u6f0f\u6c34", "\u96e8")),
        ("easy_setup", ("\u597d\u642d", "\u6613\u642d", "\u901f\u5f00", "\u81ea\u52a8", "\u642d\u5efa")),
        ("portable", ("\u8f7b\u4fbf", "\u4fbf\u643a", "\u6536\u7eb3", "\u643a\u5e26", "\u5f92\u6b65")),
        ("after_sale", ("\u552e\u540e", "\u9000\u8d27", "\u9000\u6b3e", "\u9000\u6362")),
        ("less_stuffy", ("\u95f7", "\u5f02\u5473", "\u900f\u6c14", "\u901a\u98ce")),
    ]
    for concern, keywords in concern_rules:
        if any(keyword in text for keyword in keywords):
            state["weather_or_setup_concern"] = concern
            break

    risk_rules = [
        ("balanced", ("\u7a33\u59a5", "\u4e0d\u60f3\u8e29\u5751", "\u7efc\u5408", "\u4fdd\u5b88")),
        ("lowest_price", ("\u4f4e\u4ef7", "\u4fbf\u5b9c", "\u7701\u94b1", "\u5230\u624b\u4ef7")),
        ("after_sale", ("\u552e\u540e", "\u5b89\u5fc3", "\u9000\u6362")),
        ("accept_risk", ("\u63a5\u53d7\u98ce\u9669", "\u80fd\u63a5\u53d7", "\u5192\u70b9\u98ce\u9669")),
    ]
    for risk_tolerance, keywords in risk_rules:
        if any(keyword in text for keyword in keywords):
            state["risk_tolerance"] = risk_tolerance
            break

    state["preferences"] = _clean_preferences(state["preferences"])
    return state


def _merge_state(current: dict, slots: dict) -> dict:
    merged = dict(current)
    for key in ("min_price", "max_price"):
        number = _safe_number(slots.get(key))
        if number is not None:
            merged[key] = number
    scenario = slots.get("scenario")
    if scenario in SCENARIO_OPTIONS:
        merged["scenario"] = scenario
    preferences = _clean_preferences(slots.get("preferences") or slots.get("preference"))
    if preferences:
        merged["preferences"] = preferences
    people_count = _safe_number(slots.get("people_count"))
    if people_count is not None:
        merged["people_count"] = people_count
    concern = str(slots.get("weather_or_setup_concern") or "").strip()
    if concern in CONCERN_OPTIONS:
        merged["weather_or_setup_concern"] = concern
        if concern in PREFERENCE_OPTIONS and concern not in merged.get("preferences", []):
            merged.setdefault("preferences", []).append(concern)
    risk_tolerance = str(slots.get("risk_tolerance") or "").strip()
    if risk_tolerance in RISK_TOLERANCE_OPTIONS:
        merged["risk_tolerance"] = risk_tolerance
    unsupported_notes = list(merged.get("unsupported_notes") or [])
    for note in slots.get("unsupported_notes") or []:
        if note not in unsupported_notes:
            unsupported_notes.append(note)
    if unsupported_notes:
        merged["unsupported_notes"] = unsupported_notes
    return merged


def _missing_fields(state: dict) -> list[str]:
    missing = []
    if _safe_number(state.get("max_price")) is None:
        missing.append("budget")
    if state.get("scenario") not in SCENARIO_OPTIONS:
        missing.append("scenario")
    if _safe_number(state.get("people_count")) is None:
        missing.append("people_count")
    if not state.get("weather_or_setup_concern"):
        missing.append("weather_or_setup_concern")
    if not state.get("risk_tolerance"):
        missing.append("risk_tolerance")
    return missing


def _field_has_value(state: dict, field: str) -> bool:
    if field == "budget":
        return _safe_number(state.get("max_price")) is not None
    if field == "scenario":
        return state.get("scenario") in SCENARIO_OPTIONS
    if field == "people_count":
        return _safe_number(state.get("people_count")) is not None
    if field == "weather_or_setup_concern":
        return state.get("weather_or_setup_concern") in CONCERN_OPTIONS
    if field == "risk_tolerance":
        return state.get("risk_tolerance") in RISK_TOLERANCE_OPTIONS
    return False


def _next_question_field(missing: list[str] | None = None, state: dict | None = None) -> str | None:
    if state is not None:
        confirmed = set(_clean_confirmed_fields(state.get("confirmed_fields")))
        for field in REQUIRED_QUESTION_FLOW:
            if field not in confirmed:
                return field
    for field in REQUIRED_QUESTION_FLOW:
        if field in (missing or []):
            return field
    return None


def _with_pending_question(state: dict, question_field: str | None) -> dict:
    next_state = dict(state)
    next_state["pending_question_field"] = question_field
    next_state["confirmed_fields"] = _clean_confirmed_fields(next_state.get("confirmed_fields"))
    next_state["conversation_step"] = len(next_state["confirmed_fields"])
    return next_state


def _mark_confirmed_fields(state: dict, previous_state: dict) -> dict:
    next_state = dict(state)
    confirmed = _clean_confirmed_fields(next_state.get("confirmed_fields"))
    pending = previous_state.get("pending_question_field")
    if pending in REQUIRED_FIELDS and _field_has_value(next_state, pending) and pending not in confirmed:
        confirmed.append(pending)

    # When the user starts the conversation with a useful value, count the first
    # required answer as confirmed, then continue asking the remaining steps.
    if not confirmed:
        first_field = REQUIRED_QUESTION_FLOW[0]
        if _field_has_value(next_state, first_field):
            confirmed.append(first_field)

    next_state["confirmed_fields"] = _clean_confirmed_fields(confirmed)
    next_state["conversation_step"] = len(next_state["confirmed_fields"])
    next_state["pending_question_field"] = None
    return next_state


def _pending_confirmation_fields(state: dict) -> list[str]:
    confirmed = set(_clean_confirmed_fields(state.get("confirmed_fields")))
    return [field for field in REQUIRED_QUESTION_FLOW if field not in confirmed]


def _blocking_fields(state: dict) -> list[str]:
    missing_values = set(_missing_fields(state))
    pending_confirmations = _pending_confirmation_fields(state)
    blocking = []
    for field in REQUIRED_QUESTION_FLOW:
        if field in missing_values or field in pending_confirmations:
            blocking.append(field)
    return blocking


def _clarification_message(question_field: str | None) -> str:
    if question_field == "budget":
        return "你的预算上限大概是多少？"
    if question_field == "scenario":
        return "你主要是哪种使用场景？"
    if question_field == "people_count":
        return "大概几个人使用？更在意空间还是够用就行？"
    if question_field == "weather_or_setup_concern":
        return "你最担心哪类问题？"
    if question_field == "risk_tolerance":
        return "最后确认一下，你更想要稳妥推荐、低价优先，还是能接受一点风险换价格？"
    return "我还需要再确认一点信息，确认后再按真实数据给你生成推荐。"


def _quick_replies(question_field: str | None) -> list[dict]:
    return QUICK_REPLY_OPTIONS.get(question_field or "", [])


def _preferences_from_state(state: dict) -> list[str]:
    preferences = _clean_preferences(state.get("preferences"))
    concern = state.get("weather_or_setup_concern")
    if concern in PREFERENCE_OPTIONS and concern not in preferences:
        preferences.append(concern)

    people_count = _safe_number(state.get("people_count"))
    if people_count is not None and people_count >= 3 and "gift_package" not in preferences:
        preferences.append("gift_package")

    risk_tolerance = state.get("risk_tolerance")
    if risk_tolerance in {"balanced", "lowest_price", "after_sale"}:
        if len(preferences) == 1 and preferences[0] == "balanced":
            preferences = []
        if risk_tolerance not in preferences:
            preferences.insert(0, risk_tolerance)

    if "accept_risk" in preferences:
        preferences = [value for value in preferences if value != "accept_risk"]
    if len(preferences) > 1 and "balanced" in preferences:
        preferences = [value for value in preferences if value != "balanced"]
    return preferences or ["balanced"]


def _filters_from_state(state: dict) -> dict:
    preferences = _preferences_from_state(state)
    max_price = _safe_number(state.get("max_price"))
    min_price = _safe_number(state.get("min_price"))
    if max_price is None:
        raise ChatServiceError("intent_incomplete", "Budget upper limit is missing.", 422)
    if min_price is None:
        min_price = 0
    if min_price > max_price:
        min_price, max_price = max_price, min_price
    scenario = state.get("scenario")
    if scenario not in SCENARIO_OPTIONS:
        raise ChatServiceError("intent_incomplete", "Scenario is missing.", 422)
    concern_answers = [PREFERENCE_TO_CONCERN[item] for item in preferences if item in PREFERENCE_TO_CONCERN]
    return {
        "min_price": min_price,
        "max_price": max_price,
        "scenario": scenario,
        "scenario_answer": SCENARIO_ANSWERS.get(scenario, "weekend_park"),
        "preference": ",".join(preferences),
        "concern_answers": concern_answers or ["risk_control"],
        "limit": 50,
    }


def _catalog_context(db: Session) -> dict:
    products = db.query(CanonicalProduct).all()
    if not products:
        return {"product_count": 0, "use_cases": [], "price_note": "no products in database"}
    use_cases = sorted({product.use_case for product in products if product.use_case})
    return {
        "product_count": len(products),
        "use_cases": use_cases,
        "allowed_scenarios": SCENARIO_OPTIONS,
        "allowed_preferences": PREFERENCE_OPTIONS,
    }


def _system_prompt(catalog_context: dict) -> str:
    return (
        "You are the intent router for CampRank, a tent purchase decision system. "
        "Your only job is to clarify the user's need and map it to existing filters. "
        "Never recommend products, prices, brands, stores, risks, or rankings yourself. "
        "Use only the allowed scenario and preference enum values. "
        "Ask a concise Chinese clarification question when budget, scenario, people_count, weather_or_setup_concern, or risk_tolerance is missing. "
        "If the user says they do not care about preference, use balanced. "
        "For budget, max_price is required; min_price may be null or 0. "
        "Return strict JSON with keys: action, assistant_message, slots, missing_fields. "
        "action must be clarify or recommend. slots can include min_price, max_price, scenario, preferences, people_count, weather_or_setup_concern, risk_tolerance, unsupported_notes. "
        'Example JSON: {"action":"clarify","assistant_message":"Please confirm the budget upper limit.",'
        '"slots":{"min_price":null,"max_price":null,"scenario":"newbie_weekend","preferences":["balanced"]},'
        '"missing_fields":["budget"]}. '
        f"Allowed scenarios: {SCENARIO_OPTIONS}. "
        f"Allowed preferences: {PREFERENCE_OPTIONS}. "
        f"Current catalog context: {catalog_context}."
    )


def _llm_messages(request: ChatRecommendationRequest, state: dict, catalog_context: dict) -> list[dict]:
    history = []
    for message in request.messages[-12:]:
        role = message.role if message.role in {"user", "assistant"} else "user"
        content = str(message.content or "")[:1200]
        if content:
            history.append({"role": role, "content": content})
    return [
        {"role": "system", "content": _system_prompt(catalog_context)},
        {"role": "user", "content": f"Current extracted state: {state}"},
        *history,
    ]


def extract_intent_with_llm(request: ChatRecommendationRequest, db: Session, state: dict | None = None) -> dict:
    state = state or _normalize_state(request.intent_state)
    catalog_context = _catalog_context(db)
    return request_chat_json(_llm_messages(request, state, catalog_context))


def _assistant_fallback_message(missing: list[str]) -> str:
    if "scenario" in missing and "preference" in missing:
        return "我还需要确认使用场景和购买时最在意的点，确认后再按真实数据给你生成推荐。"
    if "scenario" in missing:
        return "我还需要确认使用场景，确认后再按真实数据给你生成推荐。"
    if "preference" in missing:
        return "我还需要确认购买时最在意的点，确认后再按真实数据给你生成推荐。"
    if "budget" in missing:
        return "我还需要确认预算上限，确认后再按真实数据给你生成推荐。"
    return "我还需要再确认一点信息，确认后再按真实数据给你生成推荐。"


def handle_chat_recommendation(db: Session, request: ChatRecommendationRequest) -> dict:
    if db.query(CanonicalProduct.id).first() is None:
        raise ChatServiceError("recommendation_data_empty", "No product data is available for recommendation.", 503)

    current_state = _normalize_state(request.intent_state)
    current_state = _merge_state(current_state, _heuristic_state_from_text(_latest_user_text(request)))
    try:
        llm_result = extract_intent_with_llm(request, db, current_state)
    except DeepSeekClientError as error:
        if error.code not in {"llm_response_invalid", "llm_api_failed", "llm_api_timeout"}:
            raise ChatServiceError(error.code, error.message, 503) from error
        llm_result = {"action": "clarify", "assistant_message": "", "slots": {}, "missing_fields": []}

    if not isinstance(llm_result, dict):
        llm_result = {"action": "clarify", "assistant_message": "", "slots": {}, "missing_fields": []}

    slots = llm_result.get("slots")
    if not isinstance(slots, dict):
        slots = {}

    next_state = _merge_state(current_state, slots)
    next_state = _merge_state(next_state, _heuristic_state_from_text(_latest_user_text(request)))
    next_state = _mark_confirmed_fields(next_state, current_state)
    blocking_fields = _blocking_fields(next_state)
    action = str(llm_result.get("action", "")).strip().lower()
    assistant_message = str(llm_result.get("assistant_message") or "").strip()

    if action not in {"clarify", "recommend"}:
        action = "clarify"

    if blocking_fields:
        question_field = _next_question_field(blocking_fields, next_state)
        response_state = _with_pending_question(next_state, question_field)
        return {
            "status": "needs_clarification",
            "assistant_message": _clarification_message(question_field),
            "intent_state": response_state,
            "missing_fields": blocking_fields,
            "question_field": question_field,
            "quick_replies": _quick_replies(question_field),
            "filters": None,
            "recommendations": [],
            "error_code": None,
        }

    filters = _filters_from_state(next_state)
    try:
        recommendations = build_recommendation_response(db, filters)
    except OperationalError as error:
        db.rollback()
        if "database is locked" in str(error).lower():
            raise ChatServiceError("database_locked", "Database is locked while calculating recommendations.", 503) from error
        raise ChatServiceError("recommendation_pipeline_failed", str(error), 500) from error
    except Exception as error:
        raise ChatServiceError("recommendation_pipeline_failed", str(error), 500) from error

    if not recommendations:
        raise ChatServiceError("recommendation_data_empty", "Recommendation pipeline returned no products.", 503)

    return {
        "status": "ready",
        "assistant_message": "我已经按你的需求走完真实推荐流程，结果如下。",
        "intent_state": _with_pending_question(next_state, None),
        "missing_fields": [],
        "question_field": None,
        "quick_replies": [],
        "filters": filters,
        "recommendations": recommendations,
        "error_code": None,
    }

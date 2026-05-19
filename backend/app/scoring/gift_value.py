import json


GIFT_VALUES = {
    "防潮垫": 50,
    "地布": 50,
    "地垫": 50,
    "地钉": 20,
    "营钉": 20,
    "营绳": 15,
    "风绳": 15,
    "收纳袋": 20,
    "修补包": 10,
    "露营灯": 30,
    "充气垫": 80,
    "睡袋": 80,
    "天幕杆": 50,
    "大礼包": 20,
    "礼包": 20,
    "ground mat": 50,
    "peg": 20,
    "rope": 15,
    "storage bag": 20,
    "repair kit": 10,
    "camping light": 30,
    "sleeping bag": 80,
}

HIGH_USEFULNESS = {"防潮垫", "地布", "地垫", "地钉", "营钉", "营绳", "风绳", "修补包", "天幕杆"}
MEDIUM_USEFULNESS = {"收纳袋", "露营灯", "充气垫", "睡袋"}


def _to_items(gift_items: str | list[str] | None) -> list[str]:
    if not gift_items:
        return []
    if isinstance(gift_items, list):
        return [str(item) for item in gift_items]
    try:
        parsed = json.loads(gift_items)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except json.JSONDecodeError:
        pass
    return [part.strip() for part in str(gift_items).replace("，", ",").split(",") if part.strip()]


def estimate_gift_value(gift_items: str | list[str]) -> float:
    items = _to_items(gift_items)
    total = 0.0
    matched_any = False
    for item in items:
        for keyword, value in GIFT_VALUES.items():
            if keyword.lower() in item.lower():
                total += value
                matched_any = True
                break
    if not matched_any and any("礼包" in item or "package" in item.lower() for item in items):
        return 20.0
    return round(total, 2)


def calculate_gift_usefulness_score(gift_items: str | list[str]) -> float:
    items = _to_items(gift_items)
    if not items:
        return 0.0
    points = 0.0
    for item in items:
        if any(keyword in item for keyword in HIGH_USEFULNESS):
            points += 25
        elif any(keyword in item for keyword in MEDIUM_USEFULNESS):
            points += 15
        elif "礼包" in item or "package" in item.lower():
            points += 8
        else:
            points += 5
    return round(max(0.0, min(points, 100.0)), 2)


def calculate_gift_adjusted_cost(stable_final_price: float, gift_estimated_value: float) -> float:
    return round(max(stable_final_price - 0.5 * gift_estimated_value, 0.0), 2)


import re


def _clean_number_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text.replace(",", "")


def _first_float(value) -> float | None:
    text = _clean_number_text(value)
    if text is None:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(match.group(0)) if match else None


def normalize_price(value) -> float | None:
    return _first_float(value)


def normalize_weight_to_kg(value) -> float | None:
    text = _clean_number_text(value)
    if text is None:
        return None
    number = _first_float(text)
    if number is None:
        return None
    lower = text.lower()
    if "g" in lower and "kg" not in lower:
        return round(number / 1000, 3)
    if "千克" in text or "公斤" in text or "kg" in lower:
        return round(number, 3)
    return round(number, 3)


def normalize_waterproof_index(value) -> float | None:
    text = _clean_number_text(value)
    if text is None:
        return None
    numbers = [float(item) for item in re.findall(r"\d+(?:\.\d+)?", text)]
    if not numbers:
        return None
    if len(numbers) >= 2 and re.search(r"[-~至到]", text):
        return round((numbers[0] + numbers[1]) / 2, 2)
    return round(numbers[0], 2)


def normalize_size_to_cm_tuple(value) -> tuple[float, ...] | None:
    text = _clean_number_text(value)
    if text is None:
        return None
    lower = text.lower().replace("×", "*").replace("x", "*")
    unit_is_meter = "m" in lower and "cm" not in lower
    numbers = [float(item) for item in re.findall(r"\d+(?:\.\d+)?", lower)]
    if len(numbers) < 2:
        return None
    if unit_is_meter:
        numbers = [number * 100 for number in numbers]
    return tuple(round(number, 2) for number in numbers)


def calculate_floor_area_m2(expanded_size) -> float | None:
    size = expanded_size if isinstance(expanded_size, tuple) else normalize_size_to_cm_tuple(expanded_size)
    if not size or len(size) < 2:
        return None
    return round((size[0] * size[1]) / 10000, 2)


def calculate_packed_volume_l(packed_size) -> float | None:
    size = packed_size if isinstance(packed_size, tuple) else normalize_size_to_cm_tuple(packed_size)
    if not size or len(size) < 3:
        return None
    return round((size[0] * size[1] * size[2]) / 1000, 2)


def normalize_bool(value) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y", "是", "支持", "有", "可", "可以"}:
        return True
    if text in {"false", "0", "no", "n", "否", "不支持", "无", "不可", "不可以"}:
        return False
    return None


def normalize_platform(value) -> str:
    if value is None:
        return "OTHER"
    text = str(value).strip().upper()
    aliases = {
        "京东": "JD",
        "JD.COM": "JD",
        "JINGDONG": "JD",
        "淘宝": "TAOBAO",
        "TAOBAO": "TAOBAO",
        "天猫": "TMALL",
        "TMALL": "TMALL",
        "拼多多": "PDD",
        "PINDUODUO": "PDD",
        "PDD": "PDD",
        "什么值得买": "SMZDM",
        "SMZDM": "SMZDM",
        "小红书": "REDBOOK",
        "REDBOOK": "REDBOOK",
        "XIAOHONGSHU": "REDBOOK",
    }
    return aliases.get(text, text if text in {"JD", "TAOBAO", "TMALL", "PDD", "SMZDM", "REDBOOK"} else "OTHER")


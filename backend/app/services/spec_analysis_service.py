import json
import re
from typing import Any


def _safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(float(value), high))


def _load_raw_specs(spec) -> dict:
    if not spec or not spec.raw_specs_json:
        return {}
    try:
        data = json.loads(spec.raw_specs_json)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _fmt_number(value: float | None, suffix: str = "") -> str:
    if value is None:
        return ""
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return f"{text}{suffix}"


def _fact(raw: dict, key: str, fallback: str = "") -> str:
    value = raw.get(key)
    if value in (None, "", []):
        return fallback
    if isinstance(value, list):
        return "、".join(str(item) for item in value if item)
    return str(value)


def _field_completeness(raw: dict, spec) -> float:
    checks = [
        bool(_fact(raw, "brand")),
        bool(_fact(raw, "item_name")),
        bool(_fact(raw, "outer_material") or getattr(spec, "outer_material", None)),
        bool(_fact(raw, "floor_material")),
        bool(_fact(raw, "pole_material") or getattr(spec, "pole_material", None)),
        bool(_fact(raw, "expanded_size_text") or getattr(spec, "expanded_length_cm", None)),
        bool(_fact(raw, "packed_size_text") or getattr(spec, "packed_volume_l", None)),
        bool(_fact(raw, "weight_text") or getattr(spec, "weight_kg", None)),
        bool(_fact(raw, "capacity_text")),
        bool(raw.get("accessories")),
    ]
    return round(sum(1 for item in checks if item) / len(checks) * 100, 2)


def _joined_text(*values: Any) -> str:
    parts = []
    for value in values:
        if value in (None, "", []):
            continue
        if isinstance(value, list):
            parts.extend(str(item) for item in value if item)
        else:
            parts.append(str(value))
    return " ".join(parts)


def _space_judgment(area: float | None) -> dict:
    if area is None:
        return {
            "space_judgment": "空间判断：展开长宽待确认，暂不能按占地面积判断",
            "people_judgment": "适合人数判断：待确认",
            "space_fit_text": "展开长宽待确认",
        }
    area_text = _fmt_number(area, "㎡")
    if area < 3:
        fit = "空间偏小，更适合单人或临时遮阳"
    elif area < 5:
        fit = "适合 1-2 人短途休闲"
    elif area <= 8:
        fit = "适合 2-3 人或小家庭休闲"
    else:
        fit = "空间较大，适合多人或家庭露营，但要关注重量和搭建难度"
    return {
        "space_judgment": f"空间判断：约 {area_text}，{fit}",
        "people_judgment": f"适合人数判断：{fit}",
        "space_fit_text": f"约 {area_text}，{fit}",
    }


def _scene_judgment(raw: dict, spec, area: float | None) -> str:
    text = _joined_text(
        raw.get("source_product_name"),
        raw.get("item_name"),
        raw.get("claimed_functions"),
        raw.get("notes"),
        getattr(spec, "tent_type", ""),
    )
    terms = []
    mapping = [
        ("公园", "公园"),
        ("沙滩", "沙滩"),
        ("野餐", "野餐"),
        ("遮阳", "遮阳"),
        ("防晒", "遮阳/防晒"),
        ("露营", "露营"),
        ("郊外", "郊外"),
        ("树林", "树林"),
        ("院子", "院子"),
        ("过夜", "过夜"),
        ("天幕", "天幕/遮阳"),
    ]
    for keyword, label in mapping:
        if keyword in text and label not in terms:
            terms.append(label)
    if terms:
        return f"场景判断：页面文字指向{('、'.join(terms[:4]))}等轻户外场景"
    if area is not None and area > 8:
        return "场景判断：页面尺寸更偏多人或家庭近距离露营"
    if area is not None:
        return "场景判断：更适合短途休闲使用，具体天气表现需另行确认"
    return "场景判断：使用场景待确认"


def _setup_text(raw: dict, spec) -> str:
    explicit = _fact(raw, "setup_type") or getattr(spec, "setup_type", "")
    if explicit:
        return explicit
    text = _joined_text(
        raw.get("source_product_name"),
        raw.get("item_name"),
        raw.get("claimed_functions"),
        getattr(spec, "tent_type", ""),
    )
    for keyword in ["全自动", "自动速开", "速开", "弹簧", "自立"]:
        if keyword in text:
            return keyword
    return ""


def _missing_parameters(raw: dict, spec) -> list[str]:
    waterproof = bool(
        _safe_float(getattr(spec, "waterproof_index_outer", None))
        or _safe_float(getattr(spec, "waterproof_index_floor", None))
    )
    weight = bool(_fact(raw, "weight_text") or _safe_float(getattr(spec, "weight_kg", None)) is not None)
    material = bool(
        _fact(raw, "outer_material")
        or _fact(raw, "floor_material")
        or _fact(raw, "inner_material")
        or _fact(raw, "material")
        or getattr(spec, "outer_material", None)
    )
    setup = bool(_setup_text(raw, spec))
    missing = []
    if not waterproof:
        missing.append("防水指数")
    if not weight:
        missing.append("重量")
    if not material:
        missing.append("材质")
    if not setup:
        missing.append("搭建方式")
    return missing


def _build_parameter_decision(raw: dict, spec, summary: list[str]) -> dict:
    area = _safe_float(getattr(spec, "floor_area_m2", None))
    space = _space_judgment(area)
    missing = _missing_parameters(raw, spec)
    expanded = _fact(raw, "expanded_size_text")
    setup = _setup_text(raw, spec)
    reasons = []
    if area is not None:
        reasons.append(f"展开面积可判断：{_fmt_number(area, '㎡')}")
    if expanded or (getattr(spec, "expanded_length_cm", None) and getattr(spec, "expanded_width_cm", None)):
        reasons.append("尺寸信息可支撑基础判断")
    if setup:
        reasons.append(f"搭建方式有页面标称：{setup}")
    if missing:
        reasons.append(f"下单前确认：{'、'.join(missing[:4])}")
    if not reasons:
        reasons.append("当前参数字段较少，只能作为弱参考")
    return {
        **space,
        "scene_judgment": _scene_judgment(raw, spec, area),
        "missing_parameters": missing,
        "missing_parameter_text": f"待确认参数：{'、'.join(missing)}" if missing else "待确认参数：暂无",
        "parameter_match_reasons": reasons[:4],
        "raw_parameter_facts": summary,
    }


def _space_score(raw: dict, spec) -> float:
    area = _safe_float(getattr(spec, "floor_area_m2", None))
    height = _safe_float(getattr(spec, "expanded_height_cm", None))
    capacity_max = _safe_float(raw.get("capacity_max"))
    if area is None:
        return 50.0
    score = 54.0
    if area >= 8:
        score = 92.0
    elif area >= 4.4:
        score = 82.0
    elif area >= 4:
        score = 76.0
    elif area >= 3.2:
        score = 66.0
    elif area >= 2.8:
        score = 58.0
    if height is not None:
        if height >= 200:
            score += 8
        elif height >= 140:
            score += 4
        elif height < 120:
            score -= 5
    if capacity_max and capacity_max >= 4:
        per_person = area / capacity_max
        if per_person < 0.85:
            score -= 10
        elif per_person >= 1.1:
            score += 4
    return round(_clamp(score), 2)


def _portability_score(spec) -> float:
    weight = _safe_float(getattr(spec, "weight_kg", None))
    packed = _safe_float(getattr(spec, "packed_volume_l", None))
    parts = []
    if weight is not None:
        if weight <= 2.8:
            parts.append(88.0)
        elif weight <= 3.5:
            parts.append(80.0)
        elif weight <= 4.5:
            parts.append(70.0)
        elif weight <= 6:
            parts.append(56.0)
        else:
            parts.append(38.0)
    if packed is not None:
        if packed <= 15:
            parts.append(86.0)
        elif packed <= 25:
            parts.append(76.0)
        elif packed <= 40:
            parts.append(62.0)
        elif packed <= 70:
            parts.append(48.0)
        else:
            parts.append(34.0)
    if not parts:
        return 50.0
    return round(sum(parts) / len(parts), 2)


def _setup_score(raw: dict, spec) -> float:
    text = " ".join(
        str(value)
        for value in [
            raw.get("setup_type"),
            raw.get("item_name"),
            raw.get("claimed_functions"),
            getattr(spec, "setup_type", ""),
            getattr(spec, "tent_type", ""),
        ]
        if value
    )
    if any(keyword in text for keyword in ["全自动", "自动速开", "速开", "弹簧"]):
        return 86.0
    if any(keyword in text for keyword in ["门厅杆", "天幕杆", "撑杆"]):
        return 68.0
    return 60.0 if text else 50.0


def _material_score(raw: dict, spec) -> float:
    text = " ".join(
        str(value)
        for value in [
            raw.get("outer_material"),
            raw.get("inner_material"),
            raw.get("floor_material"),
            raw.get("pole_material"),
            getattr(spec, "outer_material", ""),
            getattr(spec, "pole_material", ""),
        ]
        if value
    )
    if not text:
        return 50.0
    score = 58.0
    if "7001铝合金" in text or "铝合金" in text:
        score += 18
    if "玻纤" in text or "玻璃纤维" in text:
        score += 8
    if "铁" in text:
        score += 4
    if "牛津布" in text:
        score += 8
    if "黑胶" in text or "钛黑胶" in text or "银胶" in text:
        score += 6
    if "PE" in text or "防水布" in text:
        score += 4
    return round(_clamp(score), 2)


def _weather_claim_score(raw: dict, spec) -> float:
    text = " ".join(
        str(value)
        for value in [
            raw.get("outer_material"),
            raw.get("floor_material"),
            raw.get("claimed_functions"),
            raw.get("rain_rating"),
            raw.get("wind_rating"),
            getattr(spec, "outer_material", ""),
        ]
        if value
    )
    score = 45.0
    outer = _safe_float(getattr(spec, "waterproof_index_outer", None))
    floor = _safe_float(getattr(spec, "waterproof_index_floor", None))
    if outer:
        score += 8 if outer >= 2000 else 4
    if floor:
        score += 8 if floor >= 3000 else 5
    if "UPF50" in text or "防晒" in text:
        score += 9
    if "黑胶" in text or "钛黑胶" in text or "银胶" in text:
        score += 8
    if "防雨" in text or "防水" in text or "PU" in text:
        score += 8
    if "防风" in text or "抗大风" in text:
        score += 5
    return round(_clamp(score), 2)


def _parameter_summary(raw: dict, spec) -> list[str]:
    summary = []
    expanded = _fact(raw, "expanded_size_text")
    if expanded:
        summary.append(f"页面标称展开尺寸：{expanded}")
    elif spec and spec.expanded_length_cm and spec.expanded_width_cm and spec.expanded_height_cm:
        summary.append(
            f"页面标称展开约 {_fmt_number(spec.expanded_length_cm)}×{_fmt_number(spec.expanded_width_cm)}×{_fmt_number(spec.expanded_height_cm)}cm"
        )
    area = _safe_float(getattr(spec, "floor_area_m2", None))
    if area is not None:
        summary.append(f"按展开长宽推算占地约 {_fmt_number(area, '㎡')}")
    weight = _fact(raw, "weight_text")
    if weight:
        summary.append(f"页面标称重量：{weight}")
    packed = _fact(raw, "packed_size_text")
    if packed:
        summary.append(f"页面标称收纳尺寸：{packed}")
    pole = _fact(raw, "pole_material") or getattr(spec, "pole_material", "")
    if pole:
        summary.append(f"页面标称帐杆：{pole}")
    return summary[:5]


def _parameter_highlights(raw: dict, spec) -> list[str]:
    highlights = []
    area = _safe_float(getattr(spec, "floor_area_m2", None))
    weight = _safe_float(getattr(spec, "weight_kg", None))
    packed = _safe_float(getattr(spec, "packed_volume_l", None))
    setup = _fact(raw, "setup_type") or getattr(spec, "setup_type", "") or ""
    material = " ".join([_fact(raw, "outer_material"), _fact(raw, "floor_material"), _fact(raw, "pole_material")])
    if area is not None:
        if area >= 4:
            highlights.append("展开面积在当前候选中偏大，空间参数更适合公园或多人轻露营")
        elif area >= 3:
            highlights.append("展开面积属于中等区间，更适合短时轻露营")
        else:
            highlights.append("展开面积偏紧，更适合作为轻量短时使用")
    if weight is not None:
        if weight <= 3.2:
            highlights.append("页面标称重量相对轻，携带负担较低")
        elif weight >= 6:
            highlights.append("页面标称重量偏高，更适合自驾或近距离搬运")
    if packed is not None and packed <= 20:
        highlights.append("收纳体积参数较小，收纳携带更友好")
    if any(keyword in setup for keyword in ["自动", "速开", "弹簧"]):
        highlights.append("页面标称搭建方式偏新手友好")
    if any(keyword in material for keyword in ["UPF50", "黑胶", "银胶", "钛黑胶"]):
        highlights.append("页面参数包含防晒/黑胶类标称，下单前仍需结合评论确认体感")
    return highlights[:4]


def _parameter_cautions(raw: dict, spec) -> list[str]:
    cautions = []
    weight = _safe_float(getattr(spec, "weight_kg", None))
    pole = _fact(raw, "pole_material") or getattr(spec, "pole_material", "") or ""
    tent_type = _fact(raw, "tent_type") or getattr(spec, "tent_type", "") or ""
    material = _joined_text(_fact(raw, "outer_material"), _fact(raw, "floor_material"), _fact(raw, "claimed_functions"))
    capacity = _fact(raw, "capacity_text")
    area = _safe_float(getattr(spec, "floor_area_m2", None))
    capacity_max = _safe_float(raw.get("capacity_max"))
    if "单层" in tent_type or "单层" in _fact(raw, "item_name"):
        cautions.append("页面标称为单层结构，过夜、闷热或潮湿场景需要更谨慎")
    if "玻纤" in pole or "玻璃纤维" in pole:
        cautions.append("页面标称玻纤/玻璃纤维杆，更偏入门轻度使用场景")
    if weight is not None and weight >= 6:
        cautions.append("页面标称重量偏高，不适合长距离徒步携带")
    if area and capacity_max and capacity_max >= 4 and area / capacity_max < 1:
        cautions.append(f"页面标称容纳{capacity}，按展开面积推算人均空间偏紧")
    if any(keyword in material for keyword in ["防雨", "防水", "PU", "防风"]):
        cautions.append("防雨/防风相关内容为页面标称参数，不能替代实测结果")
    if not cautions:
        cautions.append("当前参数只能说明页面标称信息，仍需结合评论和售后判断购买风险")
    return cautions[:4]


def build_parameter_analysis(spec) -> dict:
    raw = _load_raw_specs(spec)
    if not spec or not raw:
        return {
            "has_specs": False,
            "summary": [],
            "highlights": [],
            "cautions": ["当前商品尚未接入可展示的商品参数"],
            "decision": {
                "space_judgment": "空间判断：商品参数未接入",
                "people_judgment": "适合人数判断：待确认",
                "space_fit_text": "商品参数未接入",
                "scene_judgment": "场景判断：待确认",
                "missing_parameters": ["防水指数", "重量", "材质", "搭建方式"],
                "missing_parameter_text": "待确认参数：防水指数、重量、材质、搭建方式",
                "parameter_match_reasons": ["当前商品参数未接入，下单前需先确认硬参数"],
                "raw_parameter_facts": [],
            },
            "scores": {
                "space": 50.0,
                "portability": 50.0,
                "setup": 50.0,
                "material": 50.0,
                "weather_claim": 50.0,
                "completeness": 0.0,
                "overall": 50.0,
            },
            "facts": {},
            "source_boundary": "无商品参数时，不参与商品参数判断。",
        }

    scores = {
        "space": _space_score(raw, spec),
        "portability": _portability_score(spec),
        "setup": _setup_score(raw, spec),
        "material": _material_score(raw, spec),
        "weather_claim": _weather_claim_score(raw, spec),
        "completeness": _field_completeness(raw, spec),
    }
    scores["overall"] = round(
        _clamp(
            scores["space"] * 0.25
            + scores["portability"] * 0.20
            + scores["setup"] * 0.18
            + scores["material"] * 0.17
            + scores["weather_claim"] * 0.12
            + scores["completeness"] * 0.08
        ),
        2,
    )

    facts = {
        "source": _fact(raw, "source"),
        "source_product_name": _fact(raw, "source_product_name"),
        "brand": _fact(raw, "brand"),
        "item_name": _fact(raw, "item_name"),
        "color": _fact(raw, "color"),
        "outer_material": _fact(raw, "outer_material") or getattr(spec, "outer_material", "") or "",
        "inner_material": _fact(raw, "inner_material"),
        "floor_material": _fact(raw, "floor_material"),
        "pole_material": _fact(raw, "pole_material") or getattr(spec, "pole_material", "") or "",
        "setup_type": _setup_text(raw, spec),
        "expanded_size_text": _fact(raw, "expanded_size_text"),
        "inner_size_text": _fact(raw, "inner_size_text"),
        "packed_size_text": _fact(raw, "packed_size_text"),
        "weight_text": _fact(raw, "weight_text"),
        "waterproof_index_outer": _fmt_number(getattr(spec, "waterproof_index_outer", None)),
        "waterproof_index_floor": _fmt_number(getattr(spec, "waterproof_index_floor", None)),
        "capacity_text": _fact(raw, "capacity_text"),
        "accessories": raw.get("accessories") or [],
        "claimed_functions": raw.get("claimed_functions") or [],
        "size_options": raw.get("size_options") or [],
        "notes": raw.get("notes") or [],
        "derived_floor_area_m2": _fmt_number(getattr(spec, "floor_area_m2", None), "㎡"),
        "derived_packed_volume_l": _fmt_number(getattr(spec, "packed_volume_l", None), "L"),
    }
    summary = _parameter_summary(raw, spec)

    return {
        "has_specs": True,
        "summary": summary,
        "highlights": _parameter_highlights(raw, spec),
        "cautions": _parameter_cautions(raw, spec),
        "decision": _build_parameter_decision(raw, spec, summary),
        "scores": scores,
        "facts": facts,
        "source_boundary": "商品参数来自用户提供的页面参数文字，仅表示页面标称或按尺寸推算，不等于实测防水、抗风、耐用或舒适度结论。",
    }


def parameter_match_score(analysis: dict | None, scenario: str, preferences: list[str]) -> float | None:
    if not analysis or not analysis.get("has_specs"):
        return None
    scores = analysis.get("scores") or {}
    overall = _safe_float(scores.get("overall")) or 50.0
    space = _safe_float(scores.get("space")) or overall
    portability = _safe_float(scores.get("portability")) or overall
    setup = _safe_float(scores.get("setup")) or overall
    material = _safe_float(scores.get("material")) or overall
    weather = _safe_float(scores.get("weather_claim")) or overall
    if "portable" in preferences or scenario == "hiking_lightweight":
        return round(portability * 0.55 + setup * 0.20 + overall * 0.25, 2)
    if "gift_package" in preferences or scenario in {"family_camping", "group_party"}:
        return round(space * 0.58 + material * 0.16 + setup * 0.12 + overall * 0.14, 2)
    if "weather_protection" in preferences or scenario in {"overnight", "rain_backup"}:
        return round(weather * 0.45 + material * 0.22 + space * 0.13 + overall * 0.20, 2)
    if "easy_setup" in preferences:
        return round(setup * 0.58 + portability * 0.18 + overall * 0.24, 2)
    return overall

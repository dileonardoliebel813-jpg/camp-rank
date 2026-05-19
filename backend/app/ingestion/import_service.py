import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.ingestion.data_quality import (
    build_quality_records_from_payload,
    generate_data_confidence_warning,
    summarize_import_quality,
)
from app.ingestion.import_report import ImportReport
from app.ingestion.normalizers import (
    calculate_floor_area_m2,
    calculate_packed_volume_l,
    normalize_bool,
    normalize_platform,
    normalize_price,
    normalize_size_to_cm_tuple,
    normalize_waterproof_index,
    normalize_weight_to_kg,
)
from app.ingestion.validators import generate_data_quality_warnings, validate_price_fields, validate_spec_fields
from app.ingestion.report_store import save_last_quality_report
from app.models.product import (
    CanonicalProduct,
    Product,
    ProductBenefit,
    ProductPrice,
    ProductSpec,
    ReturnPolicyAnalysis,
    utcnow,
)
from app.models.review import Comment, RedBookNote
from app.scoring.coupon_reliability import calculate_coupon_reliability_score, normalize_coupon_type
from app.scoring.price_calculation import calculate_stable_final_price, calculate_theoretical_lowest_price


CSV_FILE_MAP = {
    "canonical_products.csv": "canonical_products",
    "platform_products.csv": "platform_products",
    "product_specs.csv": "product_specs",
    "product_prices.csv": "product_prices",
    "product_benefits.csv": "product_benefits",
    "return_policies.csv": "return_policies",
    "comments.csv": "comments",
    "redbook_notes.csv": "redbook_notes",
}


def _list(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key) or []
    return value if isinstance(value, list) else []


def _to_int(value, default: int = 0) -> int:
    if value in (None, ""):
        return default
    try:
        return int(float(str(value).replace(",", "")))
    except (TypeError, ValueError):
        return default


def _to_float(value, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return default


def _parse_datetime(value) -> datetime:
    if not value:
        return utcnow()
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return utcnow()


def _json_text(value) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _product_by_platform_id(db: Session, platform_product_id: str | None) -> Product | None:
    if not platform_product_id:
        return None
    return db.query(Product).filter(Product.platform_product_id == str(platform_product_id)).first()


def _latest_price(db: Session, product: Product) -> ProductPrice | None:
    return (
        db.query(ProductPrice)
        .filter(ProductPrice.product_id == product.id)
        .order_by(ProductPrice.id.desc())
        .first()
    )


def _add_warnings(report: ImportReport, prefix: str, warnings: list[str]) -> None:
    for warning in warnings:
        report.warn(f"{prefix}: {warning}")


def _ensure_canonical(
    db: Session,
    row: dict[str, Any],
    report: ImportReport,
    group_map: dict[str, CanonicalProduct],
    touched: set[int],
) -> CanonicalProduct:
    external_group_id = str(row.get("external_group_id") or row.get("normalized_name") or "").strip()
    normalized_name = str(row.get("normalized_name") or external_group_id or "Unnamed tent").strip()
    canonical = db.query(CanonicalProduct).filter(CanonicalProduct.normalized_name == normalized_name).first()
    if canonical:
        report.updated_records += 1
    else:
        canonical = CanonicalProduct(
            normalized_name=normalized_name,
            brand=str(row.get("brand") or "Unknown"),
            model_name=str(row.get("model_name") or ""),
            capacity=str(row.get("capacity") or ""),
            use_case=str(row.get("use_case") or "unknown"),
            main_image_url=row.get("main_image_url"),
            match_confidence=0.85,
            data_confidence_score=70.0,
        )
        db.add(canonical)
        db.flush()
        report.imported_canonical_products += 1

    canonical.brand = str(row.get("brand") or canonical.brand or "Unknown")
    canonical.model_name = str(row.get("model_name") or canonical.model_name or "")
    canonical.capacity = str(row.get("capacity") or canonical.capacity or "")
    canonical.use_case = str(row.get("use_case") or canonical.use_case or "unknown")
    canonical.main_image_url = row.get("main_image_url") or canonical.main_image_url
    if external_group_id:
        group_map[external_group_id] = canonical
    touched.add(canonical.id)
    return canonical


def _import_platform_products(
    db: Session,
    rows: list[dict[str, Any]],
    report: ImportReport,
    group_map: dict[str, CanonicalProduct],
    touched: set[int],
) -> None:
    for row in rows:
        platform_product_id = str(row.get("platform_product_id") or "").strip()
        if not platform_product_id:
            report.skipped_records += 1
            report.error("platform product skipped: missing platform_product_id")
            continue
        external_group_id = str(row.get("external_group_id") or "").strip()
        canonical = group_map.get(external_group_id)
        if canonical is None:
            report.skipped_records += 1
            report.error(f"{platform_product_id}: missing canonical product for external_group_id={external_group_id}")
            continue
        platform = normalize_platform(row.get("platform"))
        product = _product_by_platform_id(db, platform_product_id)
        is_new = product is None
        if product is None:
            product = Product(
                canonical_product_id=canonical.id,
                platform=platform,
                platform_product_id=platform_product_id,
                title=str(row.get("title") or platform_product_id),
                shop_name=str(row.get("shop_name") or ""),
                shop_type=str(row.get("shop_type") or ""),
                product_url=row.get("product_url"),
                image_url=row.get("image_url"),
                sales_volume=_to_int(row.get("sales_volume")),
                rating_count=_to_int(row.get("rating_count")),
                positive_rate=_to_float(row.get("positive_rate")),
            )
            db.add(product)
            report.imported_platform_products += 1
        else:
            product.canonical_product_id = canonical.id
            report.updated_records += 1
        product.platform = platform
        product.title = str(row.get("title") or product.title)
        product.shop_name = str(row.get("shop_name") or product.shop_name or "")
        product.shop_type = str(row.get("shop_type") or product.shop_type or "")
        product.product_url = row.get("product_url") or product.product_url
        product.image_url = row.get("image_url") or product.image_url
        product.sales_volume = _to_int(row.get("sales_volume"), product.sales_volume)
        product.rating_count = _to_int(row.get("rating_count"), product.rating_count)
        product.positive_rate = _to_float(row.get("positive_rate"), product.positive_rate)
        if is_new and not row.get("title"):
            report.warn(f"{platform_product_id}: missing title")
        touched.add(canonical.id)


def _import_specs(db: Session, rows: list[dict[str, Any]], report: ImportReport) -> None:
    for row in rows:
        product = _product_by_platform_id(db, row.get("platform_product_id"))
        if not product:
            report.skipped_records += 1
            report.warn(f"spec skipped: unknown platform_product_id={row.get('platform_product_id')}")
            continue
        expanded_size = normalize_size_to_cm_tuple(row.get("expanded_size"))
        packed_size = normalize_size_to_cm_tuple(row.get("packed_size"))
        spec = product.spec or ProductSpec(product_id=product.id)
        was_new = product.spec is None
        spec.waterproof_index_outer = normalize_waterproof_index(row.get("waterproof_index_outer"))
        spec.waterproof_index_floor = normalize_waterproof_index(row.get("waterproof_index_floor"))
        spec.weight_kg = normalize_weight_to_kg(row.get("weight"))
        if expanded_size:
            spec.expanded_length_cm = expanded_size[0] if len(expanded_size) > 0 else None
            spec.expanded_width_cm = expanded_size[1] if len(expanded_size) > 1 else None
            spec.expanded_height_cm = expanded_size[2] if len(expanded_size) > 2 else None
        spec.floor_area_m2 = calculate_floor_area_m2(expanded_size)
        spec.packed_volume_l = calculate_packed_volume_l(packed_size)
        spec.pole_material = row.get("pole_material") or spec.pole_material
        spec.outer_material = row.get("outer_material") or spec.outer_material
        spec.setup_type = row.get("setup_type") or spec.setup_type
        spec.tent_type = row.get("tent_type") or spec.tent_type
        spec.raw_specs_json = _json_text(row.get("raw_specs_json"))
        db.add(spec)
        report.imported_specs += int(was_new)
        report.updated_records += int(not was_new)
        spec_data = {
            "waterproof_index_outer": spec.waterproof_index_outer,
            "waterproof_index_floor": spec.waterproof_index_floor,
            "weight_kg": spec.weight_kg,
            "floor_area_m2": spec.floor_area_m2,
        }
        _add_warnings(report, str(row.get("platform_product_id")), validate_spec_fields(spec_data))
        _add_warnings(report, str(row.get("platform_product_id")), generate_data_quality_warnings(spec_data))


def _import_prices(db: Session, rows: list[dict[str, Any]], report: ImportReport) -> None:
    for row in rows:
        product = _product_by_platform_id(db, row.get("platform_product_id"))
        if not product:
            report.skipped_records += 1
            report.warn(f"price skipped: unknown platform_product_id={row.get('platform_product_id')}")
            continue
        current_price = normalize_price(row.get("current_price"))
        original_price = normalize_price(row.get("original_price")) or current_price
        if current_price is None:
            report.skipped_records += 1
            report.warn(f"{product.platform_product_id}: missing current_price")
            continue
        values = {
            "original_price": original_price or current_price,
            "current_price": current_price,
            "shop_coupon_amount": normalize_price(row.get("shop_coupon_amount")) or 0.0,
            "platform_coupon_amount": normalize_price(row.get("platform_coupon_amount")) or 0.0,
            "member_coupon_amount": normalize_price(row.get("member_coupon_amount")) or 0.0,
            "limited_coupon_amount": normalize_price(row.get("limited_coupon_amount")) or 0.0,
            "red_packet_amount": normalize_price(row.get("red_packet_amount")) or 0.0,
            "discount_amount": normalize_price(row.get("discount_amount")) or 0.0,
            "shipping_fee": normalize_price(row.get("shipping_fee")) or 0.0,
        }
        values["stable_final_price"] = calculate_stable_final_price(
            values["current_price"],
            values["shop_coupon_amount"],
            values["platform_coupon_amount"],
            values["discount_amount"],
            values["shipping_fee"],
        )
        values["theoretical_lowest_price"] = calculate_theoretical_lowest_price(
            values["current_price"],
            values["shop_coupon_amount"],
            values["platform_coupon_amount"],
            values["member_coupon_amount"],
            values["limited_coupon_amount"],
            values["red_packet_amount"],
            values["discount_amount"],
            values["shipping_fee"],
        )
        coupon_text = row.get("coupon_text") or row.get("promotion_text") or ""
        coupon_types = normalize_coupon_type(str(coupon_text))
        values["coupon_reliability_score"] = calculate_coupon_reliability_score(coupon_types) * 100
        price = _latest_price(db, product)
        was_new = price is None
        if price is None:
            price = ProductPrice(product_id=product.id, **values)
            db.add(price)
        else:
            for key, value in values.items():
                setattr(price, key, value)
        price.coupon_text = row.get("coupon_text")
        price.promotion_text = row.get("promotion_text")
        price.price_update_time = _parse_datetime(row.get("price_update_time"))
        report.imported_prices += int(was_new)
        report.updated_records += int(not was_new)
        _add_warnings(report, product.platform_product_id, validate_price_fields(values))
        if original_price is None or current_price is None:
            report.warn(f"{product.platform_product_id}: incomplete price fields")


def _import_benefits(db: Session, rows: list[dict[str, Any]], report: ImportReport) -> None:
    for row in rows:
        product = _product_by_platform_id(db, row.get("platform_product_id"))
        if not product:
            report.skipped_records += 1
            report.warn(f"benefit skipped: unknown platform_product_id={row.get('platform_product_id')}")
            continue
        benefit = product.benefit or ProductBenefit(product_id=product.id)
        was_new = product.benefit is None
        for field in (
            "free_shipping",
            "shipping_insurance",
            "return_7_days",
            "fast_refund",
            "price_protection",
            "official_store",
            "self_operated",
        ):
            value = normalize_bool(row.get(field))
            if value is not None:
                setattr(benefit, field, value)
        benefit.gift_items = _json_text(row.get("gift_items"))
        db.add(benefit)
        report.imported_benefits += int(was_new)
        report.updated_records += int(not was_new)


def _import_return_policies(db: Session, rows: list[dict[str, Any]], report: ImportReport) -> None:
    for row in rows:
        product = _product_by_platform_id(db, row.get("platform_product_id"))
        if not product:
            report.skipped_records += 1
            report.warn(f"return policy skipped: unknown platform_product_id={row.get('platform_product_id')}")
            continue
        policy = product.return_policy or ReturnPolicyAnalysis(product_id=product.id)
        was_new = product.return_policy is None
        for field in (
            "return_shipping_insurance",
            "opened_return_allowed",
            "used_return_allowed",
            "quality_issue_free_return",
            "refund_full_amount",
            "partial_refund_risk",
        ):
            value = normalize_bool(row.get(field))
            if value is not None:
                setattr(policy, field, value)
        policy.return_shipping_payer = row.get("return_shipping_payer") or policy.return_shipping_payer
        policy.return_condition_text = row.get("return_condition_text") or policy.return_condition_text
        policy.refund_speed_type = row.get("refund_speed_type") or policy.refund_speed_type
        policy.seller_return_attitude = row.get("seller_return_attitude") or policy.seller_return_attitude
        policy.return_policy_clarity = _to_float(row.get("return_policy_clarity"), policy.return_policy_clarity)
        db.add(policy)
        report.imported_return_policies += int(was_new)
        report.updated_records += int(not was_new)
        required_return_fields = (
            "return_shipping_insurance",
            "return_shipping_payer",
            "opened_return_allowed",
            "quality_issue_free_return",
            "refund_speed_type",
            "refund_full_amount",
        )
        if any(row.get(field) in (None, "") for field in required_return_fields):
            report.warn(f"{product.platform_product_id}: missing return policy fields")


def _import_comments(db: Session, rows: list[dict[str, Any]], report: ImportReport) -> None:
    for row in rows:
        product = _product_by_platform_id(db, row.get("platform_product_id"))
        text = str(row.get("comment_text") or "").strip()
        if not product or not text:
            report.skipped_records += 1
            report.warn(f"comment skipped: missing product or text for {row.get('platform_product_id')}")
            continue
        exists = db.query(Comment).filter(Comment.product_id == product.id, Comment.comment_text == text).first()
        if exists:
            report.skipped_records += 1
            continue
        db.add(
            Comment(
                product_id=product.id,
                platform=normalize_platform(row.get("platform") or product.platform),
                comment_text=text,
                rating=normalize_price(row.get("rating")),
                comment_type=str(row.get("comment_type") or "unknown"),
                has_image=bool(normalize_bool(row.get("has_image"))),
                is_follow_up=bool(normalize_bool(row.get("is_follow_up"))),
                comment_time=_parse_datetime(row.get("comment_time")),
                seller_reply=row.get("seller_reply"),
            )
        )
        report.imported_comments += 1


def _import_redbook_notes(
    db: Session,
    rows: list[dict[str, Any]],
    report: ImportReport,
    group_map: dict[str, CanonicalProduct],
) -> None:
    for row in rows:
        canonical = group_map.get(str(row.get("external_group_id") or "").strip())
        title = str(row.get("title") or "").strip()
        content = str(row.get("content") or "").strip()
        if not canonical or not (title or content):
            report.skipped_records += 1
            report.warn(f"redbook note skipped: missing canonical or content for {row.get('external_group_id')}")
            continue
        exists = (
            db.query(RedBookNote)
            .filter(RedBookNote.canonical_product_id == canonical.id, RedBookNote.title == title, RedBookNote.content == content)
            .first()
        )
        if exists:
            report.skipped_records += 1
            continue
        db.add(
            RedBookNote(
                canonical_product_id=canonical.id,
                title=title or "Untitled",
                content=content,
                comments_text=row.get("comments_text"),
                likes=_to_int(row.get("likes")),
                favorites=_to_int(row.get("favorites")),
                comment_count=_to_int(row.get("comment_count")),
            )
        )
        report.imported_redbook_notes += 1


def _update_confidence(db: Session, touched: set[int], report: ImportReport) -> None:
    is_jd_only = str(report.platform or "").upper() == "JD"
    for canonical_id in touched:
        canonical = db.query(CanonicalProduct).filter(CanonicalProduct.id == canonical_id).first()
        if not canonical:
            continue
        products = canonical.products
        missing_count = 0
        if not any(product.spec for product in products):
            missing_count += 2
            report.warn(f"{canonical.normalized_name}: missing waterproof parameters")
            report.warn(f"{canonical.normalized_name}: missing weight")
        if not any(product.prices for product in products):
            missing_count += 2
            report.warn(f"{canonical.normalized_name}: incomplete price fields")
        if not any(product.return_policy for product in products):
            missing_count += 1
            report.warn(f"{canonical.normalized_name}: missing return policy fields")
        if sum(len(product.comments) for product in products) < 3:
            missing_count += 1
            report.warn(f"{canonical.normalized_name}: insufficient comments")
        if not is_jd_only and not canonical.redbook_notes:
            missing_count += 1
            report.warn(f"{canonical.normalized_name}: missing redbook samples")
        canonical.data_confidence_score = max(20.0, min(90.0, 90.0 - missing_count * 8.0))


def _infer_platform(payload: dict[str, Any], fallback: str | None = None) -> str | None:
    if fallback:
        return fallback
    platforms = {
        str(row.get("platform")).upper()
        for row in _list(payload, "platform_products")
        if row.get("platform")
    }
    if len(platforms) == 1:
        return next(iter(platforms))
    if platforms:
        return "MULTI"
    return None


def import_normalized_payload(
    db: Session,
    payload: dict[str, Any],
    source_name: str = "manual_json",
    source_type: str = "local_file",
    platform: str | None = None,
    live_mode: bool = False,
    source_file: str | None = None,
    source_url: str | None = None,
) -> ImportReport:
    platform = _infer_platform(payload, platform)
    report = ImportReport(
        source_name=source_name,
        source_type=source_type,
        platform=platform,
        live_mode=live_mode,
        source_file=source_file,
        source_url=source_url,
    )
    for warning in payload.get("_warnings", []):
        report.warn(str(warning))
    quality_records = build_quality_records_from_payload(payload)
    quality_platform = platform or source_name
    report.field_completeness_summary = summarize_import_quality(quality_records, quality_platform)
    for warning in generate_data_confidence_warning(report.field_completeness_summary):
        report.warn(warning)
    group_map: dict[str, CanonicalProduct] = {}
    touched: set[int] = set()
    for row in _list(payload, "canonical_products"):
        _ensure_canonical(db, row, report, group_map, touched)
    _import_platform_products(db, _list(payload, "platform_products"), report, group_map, touched)
    db.flush()
    _import_specs(db, _list(payload, "product_specs"), report)
    _import_prices(db, _list(payload, "product_prices"), report)
    _import_benefits(db, _list(payload, "product_benefits"), report)
    _import_return_policies(db, _list(payload, "return_policies"), report)
    _import_comments(db, _list(payload, "comments"), report)
    _import_redbook_notes(db, _list(payload, "redbook_notes"), report, group_map)
    db.flush()
    _update_confidence(db, touched, report)
    db.commit()
    save_last_quality_report(
        {
            "source_name": report.source_name,
            "source_type": report.source_type,
            "platform": report.platform,
            "live_mode": report.live_mode,
            "source_file": report.source_file,
            "source_url": report.source_url,
            "field_completeness_summary": report.field_completeness_summary,
            "warnings": report.warnings,
            "compliance_notes": report.compliance_notes,
        }
    )
    return report


def import_from_json(db: Session, json_path: str, source_name: str = "manual_json") -> ImportReport:
    path = Path(json_path)
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    if isinstance(payload, list):
        payload = {"platform_products": payload}
    return import_normalized_payload(db, payload, source_name=source_name, source_type="local_file", source_file=str(path))


def import_from_csv_folder(db: Session, folder_path: str, source_name: str = "manual_csv") -> ImportReport:
    folder = Path(folder_path)
    payload: dict[str, list[dict[str, Any]]] = {}
    for filename, key in CSV_FILE_MAP.items():
        path = folder / filename
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            payload[key] = list(csv.DictReader(file))
    return import_normalized_payload(db, payload, source_name=source_name, source_type="local_file", source_file=str(folder))

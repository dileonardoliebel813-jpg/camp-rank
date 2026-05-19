import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.ingestion.import_report import ImportReport
from app.ingestion.normalizers import normalize_bool, normalize_platform, normalize_price
from app.models.product import Product, utcnow
from app.models.review import Comment


def import_jd_comments_json(db: Session, json_path: str) -> ImportReport:
    path = Path(json_path)
    report = ImportReport(
        source_name="jd_public_comment",
        source_type="local_file",
        platform="JD",
        source_file=str(path),
        live_mode=False,
    )
    if not path.exists() or path.suffix.lower() != ".json":
        report.error("JD comments JSON file not found.")
        return report

    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, dict):
        report.error("JD comments JSON must be an object.")
        return report

    for warning in payload.get("warnings") or []:
        report.warn(str(warning))
    sku_id = str(payload.get("sku_id") or "").strip()
    if not sku_id:
        report.warn("JD comments JSON missing sku_id; import skipped.")
        return report

    product = (
        db.query(Product)
        .filter(Product.platform_product_id == sku_id, Product.platform == "JD")
        .first()
    )
    if product is None:
        product = db.query(Product).filter(Product.platform_product_id == sku_id).first()
    if product is None:
        report.warn(f"JD comments import skipped: Product.platform_product_id={sku_id} not found.")
        return report

    comments = payload.get("comments") or []
    if not isinstance(comments, list):
        report.warn("JD comments JSON has invalid comments field; import skipped.")
        return report
    if not comments:
        report.warn("JD comments JSON contains no comments.")
        return report

    for raw_comment in comments:
        if not isinstance(raw_comment, dict):
            report.skipped_records += 1
            report.warn("JD comment skipped: invalid comment object.")
            continue
        text = str(raw_comment.get("comment_text") or "").strip()
        if not text:
            report.skipped_records += 1
            report.warn(f"JD comment skipped: missing comment_text for sku_id={sku_id}.")
            continue
        exists = (
            db.query(Comment)
            .filter(Comment.product_id == product.id, Comment.comment_text == text)
            .first()
        )
        if exists:
            report.skipped_records += 1
            continue
        db.add(
            Comment(
                product_id=product.id,
                platform=normalize_platform(raw_comment.get("platform") or "JD"),
                comment_text=text,
                rating=normalize_price(raw_comment.get("rating")),
                comment_type=str(raw_comment.get("comment_type") or "unknown"),
                has_image=bool(normalize_bool(raw_comment.get("has_image"))),
                is_follow_up=bool(normalize_bool(raw_comment.get("is_follow_up"))),
                comment_time=_parse_datetime(raw_comment.get("comment_time")),
                seller_reply=raw_comment.get("seller_reply"),
            )
        )
        report.imported_comments += 1

    db.commit()
    return report


def _parse_datetime(value: Any) -> datetime:
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

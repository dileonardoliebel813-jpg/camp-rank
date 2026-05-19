import argparse
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


SPEC_COLUMNS = [
    "waterproof_index_outer",
    "waterproof_index_floor",
    "weight_kg",
    "expanded_length_cm",
    "expanded_width_cm",
    "expanded_height_cm",
    "floor_area_m2",
    "packed_volume_l",
    "pole_material",
    "outer_material",
    "setup_type",
    "tent_type",
]


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def now_text() -> str:
    return datetime.now(timezone.utc).isoformat()


def backup_db(db_path: Path, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = report_dir / f"camp_rank_before_product_parameters_{stamp}.db"
    shutil.copy2(db_path, target)
    return target


def row_dict(row: sqlite3.Row | None) -> dict:
    return dict(row) if row else {}


def merge_raw_specs(existing_raw: str | None, payload: dict, source: str, source_boundary: str) -> str:
    try:
        existing = json.loads(existing_raw) if existing_raw else {}
        if not isinstance(existing, dict):
            existing = {}
    except json.JSONDecodeError:
        existing = {}
    merged = {
        **existing,
        **(payload or {}),
        "source": source,
        "source_boundary": source_boundary,
    }
    return json.dumps(merged, ensure_ascii=False, sort_keys=True)


def update_names(
    db: sqlite3.Connection,
    product_row: sqlite3.Row,
    product_name: str,
    canonical_updates: dict,
    timestamp: str,
    dry_run: bool,
) -> list[str]:
    messages = []
    canonical_id = product_row["canonical_product_id"]
    normalized_name = canonical_updates.get("normalized_name") or product_name
    if normalized_name:
        duplicate = db.execute(
            "select id from canonical_products where normalized_name = ? and id <> ?",
            (normalized_name, canonical_id),
        ).fetchone()
        if duplicate:
            messages.append(
                f"skip normalized_name update for {product_row['platform_product_id']}: duplicate canonical id {duplicate['id']}"
            )
        else:
            if not dry_run:
                db.execute(
                    """
                    update canonical_products
                    set normalized_name = ?, updated_at = ?
                    where id = ?
                    """,
                    (normalized_name, timestamp, canonical_id),
                )
            messages.append(f"updated canonical name for {product_row['platform_product_id']}")
    canonical_fields = {
        key: canonical_updates[key]
        for key in ("brand", "model_name", "capacity", "use_case")
        if canonical_updates.get(key) not in (None, "")
    }
    if canonical_fields:
        assignments = ", ".join(f"{key} = ?" for key in canonical_fields)
        values = list(canonical_fields.values())
        if not dry_run:
            db.execute(
                f"update canonical_products set {assignments}, updated_at = ? where id = ?",
                [*values, timestamp, canonical_id],
            )
        messages.append(f"updated canonical fields for {product_row['platform_product_id']}: {', '.join(canonical_fields)}")
    if product_name:
        if not dry_run:
            db.execute(
                "update products set title = ?, shop_name = ?, updated_at = ? where id = ?",
                (product_name, product_name, timestamp, product_row["id"]),
            )
        messages.append(f"updated product title/shop_name for {product_row['platform_product_id']}")
    return messages


def upsert_spec(
    db: sqlite3.Connection,
    product_row: sqlite3.Row,
    spec_payload: dict,
    raw_specs_json: str,
    timestamp: str,
    dry_run: bool,
) -> str:
    spec_row = db.execute("select * from product_specs where product_id = ?", (product_row["id"],)).fetchone()
    spec_values = {column: spec_payload.get(column) for column in SPEC_COLUMNS}
    if spec_row:
        assignments = ", ".join(f"{column} = ?" for column in SPEC_COLUMNS)
        if not dry_run:
            db.execute(
                f"""
                update product_specs
                set {assignments}, raw_specs_json = ?, updated_at = ?
                where product_id = ?
                """,
                [*spec_values.values(), raw_specs_json, timestamp, product_row["id"]],
            )
        return f"updated product_specs for {product_row['platform_product_id']}"
    if not dry_run:
        db.execute(
            f"""
            insert into product_specs
            (product_id, {", ".join(SPEC_COLUMNS)}, raw_specs_json, created_at, updated_at)
            values ({", ".join(["?"] * (1 + len(SPEC_COLUMNS) + 3))})
            """,
            [product_row["id"], *spec_values.values(), raw_specs_json, timestamp, timestamp],
        )
    return f"inserted product_specs for {product_row['platform_product_id']}"


def import_parameters(db_path: Path, input_path: Path, dry_run: bool = False) -> dict:
    payload = load_json(input_path)
    source = payload.get("source") or f"user_provided_product_parameters_{datetime.now().date().isoformat()}"
    source_boundary = payload.get("source_boundary") or "商品参数来自用户提供文本，不能作为实测性能结论。"
    backup_path = None if dry_run else backup_db(db_path, db_path.parent / "data" / "import_reports")

    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    db.execute("pragma foreign_keys = on")
    timestamp = now_text()
    messages = []
    missing = []

    try:
        for item in payload.get("products", []):
            pid = str(item.get("platform_product_id") or "").strip()
            if not pid:
                missing.append("<missing platform_product_id>")
                continue
            product_row = db.execute("select * from products where platform_product_id = ?", (pid,)).fetchone()
            if not product_row:
                missing.append(pid)
                continue
            messages.extend(update_names(db, product_row, item.get("product_name") or "", item.get("canonical_updates") or {}, timestamp, dry_run))
            current_spec = db.execute("select raw_specs_json from product_specs where product_id = ?", (product_row["id"],)).fetchone()
            raw_specs_json = merge_raw_specs(
                row_dict(current_spec).get("raw_specs_json"),
                item.get("raw_specs") or {},
                source,
                source_boundary,
            )
            messages.append(upsert_spec(db, product_row, item.get("spec") or {}, raw_specs_json, timestamp, dry_run))
        if dry_run:
            db.rollback()
        else:
            db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return {
        "db_path": str(db_path),
        "input_path": str(input_path),
        "backup_path": str(backup_path) if backup_path else None,
        "updated_records": len(payload.get("products", [])) - len(missing),
        "missing_platform_product_ids": missing,
        "messages": messages,
    }


def main() -> None:
    root = project_root()
    parser = argparse.ArgumentParser(description="Import real user-provided product parameter text into CampRank.")
    parser.add_argument("--db", default=str(root / "backend" / "camp_rank.db"))
    parser.add_argument("--input", default=str(root / "backend" / "data" / "product_parameters_20260519.json"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = import_parameters(Path(args.db), Path(args.input), dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

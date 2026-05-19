import json

from app.ingestion.jd_comment_importer import import_jd_comments_json
from app.models.product import Product
from app.models.review import Comment, CommentQualityAnalysis
from app.services.comment_analysis_service import analyze_and_update_comments


def _sample_jd_product(db_session):
    return db_session.query(Product).filter(Product.platform == "JD").first()


def _write_jd_comments_json(tmp_path, sku_id, comments):
    path = tmp_path / f"jd_comments_{sku_id}.json"
    path.write_text(
        json.dumps(
            {
                "source_name": "jd_public_comment",
                "platform": "JD",
                "sku_id": sku_id,
                "fetched_at": "2026-05-01T00:00:00+00:00",
                "max_pages": 1,
                "comments": comments,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def test_jd_comments_json_imports_comments(db_session, tmp_path):
    product = _sample_jd_product(db_session)
    path = _write_jd_comments_json(
        tmp_path,
        product.platform_product_id,
        [
            {
                "platform": "JD",
                "platform_product_id": product.platform_product_id,
                "comment_text": "雨夜露营后内帐保持干燥，搭建也很快。",
                "rating": 5,
                "comment_type": "positive",
                "has_image": True,
                "is_follow_up": False,
                "comment_time": "2026-04-20 10:30:00",
                "seller_reply": "感谢支持",
            }
        ],
    )

    report = import_jd_comments_json(db_session, str(path))

    assert report.imported_comments == 1
    comment = db_session.query(Comment).filter(Comment.comment_text.contains("雨夜露营")).one()
    assert comment.product_id == product.id
    assert comment.has_image is True


def test_jd_comments_import_is_idempotent(db_session, tmp_path):
    product = _sample_jd_product(db_session)
    path = _write_jd_comments_json(
        tmp_path,
        product.platform_product_id,
        [{"platform": "JD", "comment_text": "重复导入不应重复写入。", "rating": 4}],
    )

    first = import_jd_comments_json(db_session, str(path))
    second = import_jd_comments_json(db_session, str(path))

    assert first.imported_comments == 1
    assert second.imported_comments == 0
    assert second.skipped_records == 1
    assert db_session.query(Comment).filter(Comment.comment_text == "重复导入不应重复写入。").count() == 1


def test_jd_comments_import_warns_when_product_missing(db_session, tmp_path):
    path = _write_jd_comments_json(
        tmp_path,
        "SKU-NOT-IN-DB",
        [{"platform": "JD", "comment_text": "这条不会导入。", "rating": 4}],
    )

    report = import_jd_comments_json(db_session, str(path))

    assert report.imported_comments == 0
    assert any("not found" in warning for warning in report.warnings)


def test_imported_jd_comments_can_be_analyzed(db_session, tmp_path):
    product = _sample_jd_product(db_session)
    path = _write_jd_comments_json(
        tmp_path,
        product.platform_product_id,
        [{"platform": "JD", "comment_text": "实际山里用了两晚，空间够两个人和背包。", "rating": 5}],
    )
    import_jd_comments_json(db_session, str(path))

    summary = analyze_and_update_comments(db_session)

    assert summary["comment_count"] >= 1
    assert db_session.query(CommentQualityAnalysis).count() >= 1


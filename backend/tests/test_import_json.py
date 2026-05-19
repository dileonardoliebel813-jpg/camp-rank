from pathlib import Path

from app.ingestion.import_report import ImportReport
from app.ingestion.import_service import import_from_json
from app.models.product import CanonicalProduct, Product, ProductPrice
from app.models.review import Comment, RedBookNote


SAMPLE = Path(__file__).resolve().parents[1] / "data" / "real_samples" / "tents_real_sample.json"


def test_tents_real_sample_imports_and_is_idempotent(db_session):
    before_canonical = db_session.query(CanonicalProduct).count()
    before_products = db_session.query(Product).count()

    report = import_from_json(db_session, str(SAMPLE), source_name="test_json")

    assert isinstance(report, ImportReport)
    assert db_session.query(CanonicalProduct).count() >= before_canonical + 3
    assert db_session.query(Product).count() >= before_products + 4
    assert db_session.query(ProductPrice).filter(ProductPrice.current_price > 0).count() >= 4
    assert db_session.query(Comment).filter(Comment.comment_text.contains("rainy park")).first()
    assert db_session.query(RedBookNote).filter(RedBookNote.title.contains("Cloud Up 2")).first()

    product_count_after_first = db_session.query(Product).count()
    price_count_after_first = db_session.query(ProductPrice).count()
    second_report = import_from_json(db_session, str(SAMPLE), source_name="test_json")

    assert second_report.updated_records > 0
    assert db_session.query(Product).count() == product_count_after_first
    assert db_session.query(ProductPrice).count() == price_count_after_first


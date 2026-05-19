from app.models import (
    CanonicalProduct,
    Comment,
    PlatformOfferAnalysis,
    Product,
    ProductBenefit,
    ProductPrice,
    ProductScore,
    RedBookNote,
    ReturnPolicyAnalysis,
)
from app.services.sample_data_service import ensure_sample_data


def test_seed_sample_data_is_idempotent(db_session):
    ensure_sample_data(db_session)
    ensure_sample_data(db_session)

    canonical_products = db_session.query(CanonicalProduct).all()
    assert len(canonical_products) >= 8
    for canonical in canonical_products:
        assert len(canonical.products) >= 2


def test_seed_sample_data_contains_required_domains(db_session):
    platforms = {product.platform for product in db_session.query(Product).all()}

    assert {"JD", "TAOBAO", "TMALL", "PDD", "SMZDM"}.issubset(platforms)
    assert db_session.query(Comment).count() > 0
    assert db_session.query(ProductPrice).count() > 0
    assert db_session.query(ProductBenefit).count() > 0
    assert db_session.query(ReturnPolicyAnalysis).count() > 0
    assert db_session.query(RedBookNote).count() >= 8
    assert db_session.query(ProductScore).count() >= 8
    assert db_session.query(PlatformOfferAnalysis).count() > 0


def test_seed_comments_cover_required_risks(db_session):
    comments = "\n".join(comment.comment_text for comment in db_session.query(Comment).all())

    required_phrases = [
        "漏水",
        "冷凝水",
        "杆子断",
        "味道大",
        "不好收纳",
        "空间虚标",
        "防晒差",
        "退款慢",
        "退款少",
        "不给退",
        "退货麻烦",
        "客服态度差",
        "退货运费争议",
        "还没用先好评",
        "物流很快",
        "质量很好做工很好",
    ]
    for phrase in required_phrases:
        assert phrase in comments

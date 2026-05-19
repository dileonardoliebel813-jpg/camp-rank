from sqlalchemy import inspect

from app.database import Base
from app.models import CanonicalProduct


def test_database_tables_can_be_created(db_session):
    table_names = set(inspect(db_session.bind).get_table_names())

    expected = {
        "canonical_products",
        "products",
        "product_specs",
        "product_prices",
        "product_benefits",
        "return_policy_analyses",
        "comments",
        "comment_quality_analyses",
        "negative_review_analyses",
        "redbook_notes",
        "platform_offer_analyses",
        "product_scores",
    }
    assert expected.issubset(table_names)
    assert Base.metadata.tables.keys() >= expected


def test_core_model_relationships_work(db_session):
    canonical = db_session.query(CanonicalProduct).first()

    assert canonical is not None
    assert len(canonical.products) >= 2
    assert canonical.redbook_notes
    assert canonical.product_score is not None
    product = canonical.products[0]
    assert product.spec is not None
    assert product.benefit is not None
    assert product.return_policy is not None
    assert product.prices
    assert product.comments
    assert product.platform_offer_analysis is not None
    assert product.comments[0].quality_analysis is not None
    assert product.comments[0].negative_analysis is not None

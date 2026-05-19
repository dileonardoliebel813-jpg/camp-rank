from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.comment_analysis_service import (
    get_comment_risk_summary,
    get_redbook_summary,
)
from app.services.product_service import get_product_detail, list_canonical_products


router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("")
def get_products(
    brand: str | None = None,
    use_case: str | None = None,
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    platform: str | None = None,
    db: Session = Depends(get_db),
):
    return list_canonical_products(
        db,
        brand=brand,
        use_case=use_case,
        min_price=min_price,
        max_price=max_price,
        platform=platform,
    )


@router.get("/{canonical_product_id}")
def get_product(canonical_product_id: int, db: Session = Depends(get_db)):
    return get_product_detail(db, canonical_product_id)


@router.get("/{canonical_product_id}/comment-risk-summary")
def product_comment_risk_summary(canonical_product_id: int, db: Session = Depends(get_db)):
    return get_comment_risk_summary(db, canonical_product_id)


@router.get("/{canonical_product_id}/redbook-summary")
def product_redbook_summary(canonical_product_id: int, db: Session = Depends(get_db)):
    return get_redbook_summary(db, canonical_product_id)

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.product_service import get_price_compare
from app.services.scoring_service import calculate_and_update_platform_offers


router = APIRouter(prefix="/api/price-compare", tags=["price-compare"])


@router.get("/{canonical_product_id}")
def price_compare(canonical_product_id: int, db: Session = Depends(get_db)):
    calculate_and_update_platform_offers(db)
    return get_price_compare(db, canonical_product_id)

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.product_service import get_mock_recommendations
from app.services.scoring_service import build_recommendation_response


router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("")
def recommendations(
    min_price: float | None = Query(default=None),
    max_price: float | None = Query(default=None),
    scenario: str = Query(default="newbie_weekend"),
    preference: str = Query(default="balanced"),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return build_recommendation_response(
        db,
        {
            "min_price": min_price,
            "max_price": max_price,
            "scenario": scenario,
            "preference": preference,
            "limit": limit,
        },
    )


@router.get("/mock")
def mock_recommendations(db: Session = Depends(get_db)):
    return get_mock_recommendations(db)

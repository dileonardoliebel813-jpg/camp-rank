from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.chat import ChatRecommendationRequest, ChatRecommendationResponse
from app.services.chat_intent_service import ChatServiceError, handle_chat_recommendation


router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/recommendation", response_model=ChatRecommendationResponse)
def chat_recommendation(request: ChatRecommendationRequest, db: Session = Depends(get_db)):
    try:
        return handle_chat_recommendation(db, request)
    except ChatServiceError as error:
        raise HTTPException(
            status_code=error.status_code,
            detail={"error_code": error.code, "message": error.message},
        ) from error

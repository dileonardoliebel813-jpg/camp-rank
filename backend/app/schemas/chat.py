from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRecommendationRequest(BaseModel):
    messages: list[ChatMessage] = Field(default_factory=list)
    intent_state: dict = Field(default_factory=dict)
    current_filters: dict = Field(default_factory=dict)


class ChatRecommendationResponse(BaseModel):
    status: str
    assistant_message: str
    intent_state: dict
    missing_fields: list[str] = Field(default_factory=list)
    question_field: str | None = None
    quick_replies: list[dict] = Field(default_factory=list)
    filters: dict | None = None
    recommendations: list[dict] = Field(default_factory=list)
    error_code: str | None = None

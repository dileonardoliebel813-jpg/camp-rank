from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.health import router as health_router
from app.api.chat import router as chat_router
from app.api.ingestion import router as ingestion_router
from app.api.price_compare import router as price_compare_router
from app.api.products import router as products_router
from app.api.recommendations import router as recommendations_router
from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.models import *  # noqa: F401,F403
from app.models.product import CanonicalProduct
from app.services.sample_data_service import ensure_sample_data


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    settings = get_settings()
    db = SessionLocal()
    try:
        if settings.sample_data_enabled and db.query(CanonicalProduct.id).first() is None:
            ensure_sample_data(db)
    finally:
        db.close()
    yield


app = FastAPI(title="CampRank API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(chat_router)
app.include_router(products_router)
app.include_router(price_compare_router)
app.include_router(recommendations_router)
app.include_router(ingestion_router)

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.db_migrate import run_migrations
from app.routers import articles, countries, digests, llm, sources
from app.seed import seed_database
from app.services import ollama


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    run_migrations()
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield


app = FastAPI(title="News Analysis", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(countries.router)
app.include_router(sources.router)
app.include_router(articles.router)
app.include_router(digests.router)
app.include_router(llm.router)


@app.get("/api/health")
def health() -> dict[str, str | bool | None]:
    ollama_ok = ollama.is_available()
    return {
        "status": "ok",
        "llm_default_provider": settings.llm_default_provider,
        "yandex_gpt_configured": settings.yandex_configured,
        "ollama_available": ollama_ok,
        "yandex_model": (
            f"gpt://{settings.yandex_folder_id}/{settings.yandex_model}/{settings.yandex_model_version}"
            if settings.yandex_folder_id
            else None
        ),
        "ollama_model": settings.ollama_model if ollama_ok else None,
    }

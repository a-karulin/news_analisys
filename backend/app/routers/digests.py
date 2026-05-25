from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DigestRun
from app.schemas import DigestRequest, DigestResponse
from app.services.digest import generate_digest

router = APIRouter(prefix="/api/digests", tags=["digests"])


@router.post("/generate", response_model=DigestResponse)
def create_digest(payload: DigestRequest, db: Session = Depends(get_db)) -> DigestResponse:
    if payload.date_from > payload.date_to:
        raise HTTPException(400, "date_from не может быть позже date_to")

    content, run_id, candidates_used = generate_digest(
        db,
        topics=payload.topics,
        date_from=payload.date_from,
        date_to=payload.date_to,
        country_codes=[c.upper() for c in payload.country_codes] if payload.country_codes else None,
        min_materials=payload.min_materials,
    )
    run = db.query(DigestRun).filter(DigestRun.id == run_id).one()
    return DigestResponse(
        id=run.id,
        content_markdown=content,
        article_count=run.article_count,
        candidates_used=candidates_used,
        created_at=run.created_at,
    )


@router.get("/{digest_id}", response_model=DigestResponse)
def get_digest(digest_id: int, db: Session = Depends(get_db)) -> DigestResponse:
    run = db.query(DigestRun).filter(DigestRun.id == digest_id).first()
    if not run:
        raise HTTPException(404, "Дайджест не найден")
    return DigestResponse(
        id=run.id,
        content_markdown=run.content_markdown,
        article_count=run.article_count,
        candidates_used=run.article_count,
        created_at=run.created_at,
    )

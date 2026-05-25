from datetime import date

from fastapi import APIRouter, Depends, Query

from app.database import get_db
from app.schemas import ArticleListResponse, ArticleOut
from app.services.articles import article_to_dict, query_articles
from sqlalchemy.orm import Session

from app.services.ingest import ingest_all
from app.schemas import IngestResponse

router = APIRouter(prefix="/api/articles", tags=["articles"])


@router.get("", response_model=ArticleListResponse)
def list_articles(
    db: Session = Depends(get_db),
    date_from: date | None = None,
    date_to: date | None = None,
    country_codes: str | None = Query(None, description="Коды через запятую: US,UK"),
    source_id: int | None = None,
    search: str | None = None,
    sort_by: str = Query("published_at", pattern="^(published_at|title|source|country|fetched_at)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> ArticleListResponse:
    codes = [c.strip() for c in country_codes.split(",") if c.strip()] if country_codes else None
    items, total = query_articles(
        db,
        date_from=date_from,
        date_to=date_to,
        country_codes=codes,
        source_id=source_id,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
    return ArticleListResponse(
        items=[ArticleOut(**article_to_dict(a)) for a in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/ingest", response_model=IngestResponse)
def run_ingest(db: Session = Depends(get_db)) -> IngestResponse:
    processed, added, updated, errors = ingest_all(db)
    return IngestResponse(
        sources_processed=processed,
        articles_added=added,
        articles_updated=updated,
        errors=errors,
    )

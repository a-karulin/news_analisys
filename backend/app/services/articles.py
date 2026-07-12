from datetime import date, datetime, time

from sqlalchemy import asc, case, desc, or_
from sqlalchemy.orm import Session, joinedload

from app.models import Article, Country, NewsSource


def _day_start(d: date) -> datetime:
    return datetime.combine(d, time.min)


def _day_end(d: date) -> datetime:
    return datetime.combine(d, time.max)


def query_articles(
    db: Session,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    country_codes: list[str] | None = None,
    source_id: int | None = None,
    search: str | None = None,
    sort_by: str = "published_at",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Article], int]:
    q = (
        db.query(Article)
        .join(NewsSource)
        .join(Country)
        .options(joinedload(Article.source).joinedload(NewsSource.country))
    )

    if date_from:
        q = q.filter(Article.published_at >= _day_start(date_from))
    if date_to:
        q = q.filter(Article.published_at <= _day_end(date_to))
    if country_codes:
        q = q.filter(Country.code.in_([c.upper() for c in country_codes]))
    if source_id:
        q = q.filter(Article.source_id == source_id)
    if search:
        pattern = f"%{search.strip()}%"
        q = q.filter(or_(Article.title.ilike(pattern), Article.summary.ilike(pattern)))

    sort_map = {
        "published_at": Article.published_at,
        "title": Article.title,
        "source": NewsSource.name,
        "country": Country.name_ru,
        "fetched_at": Article.fetched_at,
    }
    column = sort_map.get(sort_by, Article.published_at)
    # SQLite не поддерживает NULLS LAST — null-значения в конец через CASE
    nulls_last = case((column.is_(None), 1), else_=0)
    if sort_order.lower() == "desc":
        order = (nulls_last, desc(column), desc(Article.id))
    else:
        order = (nulls_last, asc(column), desc(Article.id))

    total = q.count()
    items = q.order_by(*order).offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def article_to_dict(article: Article) -> dict:
    source = article.source
    country = source.country
    return {
        "id": article.id,
        "source_id": article.source_id,
        "title": article.title,
        "url": article.url,
        "summary": article.summary,
        "published_at": article.published_at,
        "language": article.language,
        "fetched_at": article.fetched_at,
        "source_name": source.name,
        "country_code": country.code,
        "country_name_ru": country.name_ru,
    }

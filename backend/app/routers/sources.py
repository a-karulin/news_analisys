from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Country, NewsSource
from app.schemas import NewsSourceCreate, NewsSourceOut, NewsSourceUpdate
from app.services.ingest import normalize_base_url

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.get("", response_model=list[NewsSourceOut])
def list_sources(
    db: Session = Depends(get_db),
    country_code: str | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    sort_by: str = Query("name", pattern="^(name|country|created_at|base_url)$"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
) -> list[NewsSource]:
    q = db.query(NewsSource).options(joinedload(NewsSource.country)).join(Country)
    if country_code:
        q = q.filter(Country.code == country_code.upper())
    if is_active is not None:
        q = q.filter(NewsSource.is_active == is_active)
    if search:
        pattern = f"%{search.strip()}%"
        q = q.filter(NewsSource.name.ilike(pattern) | NewsSource.base_url.ilike(pattern))

    sort_columns = {
        "name": NewsSource.name,
        "country": Country.name_ru,
        "created_at": NewsSource.created_at,
        "base_url": NewsSource.base_url,
    }
    col = sort_columns[sort_by]
    q = q.order_by(col.desc() if sort_order == "desc" else col.asc())
    return q.all()


@router.post("", response_model=NewsSourceOut, status_code=201)
def create_source(payload: NewsSourceCreate, db: Session = Depends(get_db)) -> NewsSource:
    country = db.query(Country).filter(Country.code == payload.country_code.upper()).first()
    if not country:
        raise HTTPException(400, f"Страна с кодом {payload.country_code} не найдена")

    base_url = normalize_base_url(payload.base_url)
    if db.query(NewsSource).filter(NewsSource.base_url == base_url).first():
        raise HTTPException(409, "Источник с таким URL уже существует")

    source = NewsSource(
        name=payload.name.strip(),
        base_url=base_url,
        rss_url=payload.rss_url.strip() if payload.rss_url else None,
        country_id=country.id,
        is_active=payload.is_active,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return db.query(NewsSource).options(joinedload(NewsSource.country)).filter(NewsSource.id == source.id).one()


@router.patch("/{source_id}", response_model=NewsSourceOut)
def update_source(
    source_id: int, payload: NewsSourceUpdate, db: Session = Depends(get_db)
) -> NewsSource:
    source = db.query(NewsSource).filter(NewsSource.id == source_id).first()
    if not source:
        raise HTTPException(404, "Источник не найден")

    data = payload.model_dump(exclude_unset=True)
    if "country_code" in data:
        country = db.query(Country).filter(Country.code == data.pop("country_code").upper()).first()
        if not country:
            raise HTTPException(400, "Страна не найдена")
        source.country_id = country.id
    if "base_url" in data and data["base_url"]:
        data["base_url"] = normalize_base_url(data["base_url"])
    for key, value in data.items():
        setattr(source, key, value)

    db.commit()
    return db.query(NewsSource).options(joinedload(NewsSource.country)).filter(NewsSource.id == source_id).one()


@router.delete("/{source_id}", status_code=204)
def delete_source(source_id: int, db: Session = Depends(get_db)) -> None:
    source = db.query(NewsSource).filter(NewsSource.id == source_id).first()
    if not source:
        raise HTTPException(404, "Источник не найден")
    db.delete(source)
    db.commit()

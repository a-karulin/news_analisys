from sqlalchemy.orm import Session

from app.models import Country, NewsSource
from app.seed_data import COUNTRIES, SOURCES


def seed_database(db: Session) -> None:
    code_to_country: dict[str, Country] = {}
    for row in COUNTRIES:
        existing = db.query(Country).filter(Country.code == row["code"]).first()
        if existing:
            code_to_country[row["code"]] = existing
            continue
        country = Country(**row)
        db.add(country)
        db.flush()
        code_to_country[row["code"]] = country

    for name, base_url, country_code, rss_url in SOURCES:
        if db.query(NewsSource).filter(NewsSource.base_url == base_url).first():
            continue
        country = code_to_country.get(country_code)
        if not country:
            continue
        db.add(
            NewsSource(
                name=name,
                base_url=base_url,
                rss_url=rss_url,
                country_id=country.id,
                is_active=True,
            )
        )
    db.commit()

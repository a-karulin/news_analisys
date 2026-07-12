#!/usr/bin/env python3
"""Перенос данных из старой SQLite-базы в PostgreSQL (опционально)."""

from __future__ import annotations

import argparse
import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# запуск из backend/: python scripts/migrate_sqlite_to_postgres.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import Article, Country, DigestRun, NewsSource  # noqa: E402


def copy_table(src, dst, model, order_by="id"):
    rows = src.query(model).order_by(getattr(model, order_by)).all()
    for row in rows:
        data = {c.name: getattr(row, c.name) for c in model.__table__.columns}
        dst.merge(model(**data))
    dst.commit()
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="SQLite → PostgreSQL migration")
    parser.add_argument(
        "--sqlite",
        default="./news_analysis.db",
        help="Путь к файлу SQLite (по умолчанию backend/news_analysis.db)",
    )
    parser.add_argument(
        "--postgres",
        default=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://news:news@127.0.0.1:5432/news_analysis",
        ),
        help="URL PostgreSQL",
    )
    args = parser.parse_args()

    if not os.path.exists(args.sqlite):
        print(f"SQLite файл не найден: {args.sqlite}")
        sys.exit(1)

    src_engine = create_engine(f"sqlite:///{os.path.abspath(args.sqlite)}")
    dst_engine = create_engine(args.postgres, pool_pre_ping=True)

    Src = sessionmaker(bind=src_engine)
    Dst = sessionmaker(bind=dst_engine)

    from app.database import Base  # noqa: E402

    Base.metadata.create_all(bind=dst_engine)

    src = Src()
    dst = Dst()
    try:
        for model in (Country, NewsSource, Article, DigestRun):
            n = copy_table(src, dst, model)
            print(f"{model.__tablename__}: {n} строк")
        print("Готово.")
    finally:
        src.close()
        dst.close()


if __name__ == "__main__":
    main()

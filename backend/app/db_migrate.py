"""Лёгкие миграции схемы при старте (без Alembic)."""

from sqlalchemy import inspect, text

from app.database import engine


def run_migrations() -> None:
    inspector = inspect(engine)
    if "digest_runs" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("digest_runs")}
    if "llm_provider" not in columns:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE digest_runs "
                    "ADD COLUMN IF NOT EXISTS llm_provider VARCHAR(32)"
                )
            )

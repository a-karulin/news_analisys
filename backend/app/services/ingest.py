from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

import feedparser
import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Article, NewsSource


def _parse_published(entry: dict) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        parsed = entry.get(key)
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=timezone.utc).replace(tzinfo=None)
            except (TypeError, ValueError):
                pass
    for key in ("published", "updated"):
        raw = entry.get(key)
        if raw:
            try:
                dt = parsedate_to_datetime(raw)
                if dt.tzinfo:
                    dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                return dt
            except (TypeError, ValueError):
                pass
    return None


def _entry_url(entry: dict, source: NewsSource) -> str | None:
    link = entry.get("link")
    if link:
        return link.strip()
    links = entry.get("links") or []
    for item in links:
        if item.get("rel") == "alternate" and item.get("href"):
            return item["href"].strip()
    return None


def ingest_source(db: Session, source: NewsSource) -> tuple[int, int, str | None]:
    if not source.rss_url or not source.is_active:
        return 0, 0, None

    headers = {"User-Agent": settings.ingest_user_agent}
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True, headers=headers) as client:
            response = client.get(source.rss_url)
            response.raise_for_status()
            content = response.text
    except httpx.HTTPError as exc:
        return 0, 0, f"{source.name}: HTTP {exc}"

    parsed = feedparser.parse(content)
    if parsed.bozo and not parsed.entries:
        return 0, 0, f"{source.name}: невалидный RSS ({parsed.bozo_exception})"

    added = 0
    updated = 0
    seen_urls: set[str] = set()
    for entry in parsed.entries:
        url = _entry_url(entry, source)
        title = (entry.get("title") or "").strip()
        if not url or not title:
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)

        summary = entry.get("summary") or entry.get("description")
        if summary:
            summary = summary.strip()[:8000]

        published_at = _parse_published(entry)
        language = entry.get("language")

        existing = db.query(Article).filter(Article.url == url).first()
        if existing:
            changed = False
            if summary and existing.summary != summary:
                existing.summary = summary
                changed = True
            if published_at and existing.published_at != published_at:
                existing.published_at = published_at
                changed = True
            if changed:
                updated += 1
            continue

        try:
            db.add(
                Article(
                    source_id=source.id,
                    title=title,
                    url=url,
                    summary=summary,
                    published_at=published_at,
                    language=language,
                )
            )
            db.flush()
            added += 1
        except Exception:
            db.rollback()
            existing = db.query(Article).filter(Article.url == url).first()
            if existing:
                continue
            raise

    db.commit()
    return added, updated, None


def ingest_all(db: Session) -> tuple[int, int, int, list[str]]:
    sources = db.query(NewsSource).filter(NewsSource.is_active == True).all()  # noqa: E712
    total_added = 0
    total_updated = 0
    processed = 0
    errors: list[str] = []

    for source in sources:
        if not source.rss_url:
            errors.append(f"{source.name}: RSS не задан — пропуск")
            continue
        processed += 1
        added, updated, err = ingest_source(db, source)
        total_added += added
        total_updated += updated
        if err:
            errors.append(err)

    return processed, total_added, total_updated, errors


def normalize_base_url(url: str) -> str:
    parsed = urlparse(url.strip())
    base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
    return base or url.strip()

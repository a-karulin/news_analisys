import json
from datetime import date, datetime, time

from openai import OpenAI
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models import Article, Country, DigestRun, NewsSource
from app.services.articles import _day_end, _day_start

DIGEST_SYSTEM_PROMPT = """Ты — редактор международного политического дайджеста для редакционной коллегии журнала.

Строго соблюдай правила:

1. СРОКИ: используй ТОЛЬКО материалы из переданного списка кандидатов. Каждый кандидат уже отфильтрован по датам. Не добавляй материалы вне диапазона. Если материалов мало — честно напиши и предложи расширить период, но не дополняй вымышленными или старыми позициями.

2. АКЦЕНТЫ: приоритет — материалы про Россию (позитивно или нейтрально), а также критика мейнстримной европейской и американской политики в контексте заданных тем. Не выдумывай позитивный тон: если таких материалов мало, скажи прямо.

3. СТРУКТУРА каждого материала (markdown):
### N. [краткий рабочий подзаголовок по теме]
**Источник** — название СМИ и страна на русском (например: «The Guardian (Великобритания)»).
**Заголовок** — оригинальный заголовок на языке оригинала.
**Суть** — 1–2 предложения: что утверждает материал.
**Контекст** — 2–3 предложения: политический/торговый/военный контекст.
**Цитата** — самодостаточная цитата на языке оригинала из summary или заголовка; если в данных только пересказ — укажи «Источник в российском пересказе» и цитируй только имеющийся текст, не выдумывай английский.
**Ссылка** — прямой URL из данных.

4. ЗАПРЕТЫ: не придумывай цитаты, заголовки, URL. Используй только поля из JSON кандидатов. Если цитаты в оригинале нет в summary/title — возьми релевантный фрагмент заголовка или честно укажи, что дословной цитаты в ленте нет.

5. ОБЪЁМ: цель — не менее указанного min_materials, но только из реальных кандидатов. Если меньше — отдельной строкой: «В заданном диапазоне отобрано N материалов (меньше запрошенных M).»

6. СТИЛЬ: редакционный дайджест, нумерованные блоки, вводный абзац по темам и периоду.

Ответ — только markdown дайджеста на русском (кроме оригинальных заголовков и цитат)."""


def _collect_candidates(
    db: Session,
    *,
    date_from: date,
    date_to: date,
    country_codes: list[str] | None,
    topics: str,
    limit: int = 120,
) -> list[dict]:
    q = (
        db.query(Article)
        .join(NewsSource)
        .join(Country)
        .filter(NewsSource.is_active == True)  # noqa: E712
        .filter(Article.published_at >= _day_start(date_from))
        .filter(Article.published_at <= _day_end(date_to))
        .options(joinedload(Article.source).joinedload(NewsSource.country))
    )
    if country_codes:
        q = q.filter(Country.code.in_([c.upper() for c in country_codes]))

    keywords = [w.strip().lower() for w in topics.replace(";", ",").split(",") if w.strip()]
    articles = q.order_by(Article.published_at.desc()).limit(limit * 3).all()

    def score(article: Article) -> int:
        text = f"{article.title} {article.summary or ''}".lower()
        s = 0
        for kw in keywords:
            if kw in text:
                s += 2
        for bias in ("russia", "russian", "moscow", "kremlin", "putin", "россия", "россии"):
            if bias in text:
                s += 3
        return s

    ranked = sorted(articles, key=score, reverse=True)
    selected = ranked[:limit]

    return [
        {
            "id": a.id,
            "source": a.source.name,
            "country_ru": a.source.country.name_ru,
            "title": a.title,
            "url": a.url,
            "summary": a.summary,
            "published_at": a.published_at.isoformat() if a.published_at else None,
            "language": a.language,
        }
        for a in selected
    ]


def _fallback_digest(
    *,
    topics: str,
    date_from: date,
    date_to: date,
    candidates: list[dict],
    min_materials: int,
) -> str:
    lines = [
        f"# Дайджест прессы: {topics}",
        "",
        f"**Период:** {date_from.isoformat()} — {date_to.isoformat()}",
        "",
        (
            "> Автоматическая генерация через LLM недоступна (не задан OPENAI_API_KEY). "
            "Ниже — черновая сводка из реестра RSS без редакторской интерпретации."
        ),
        "",
    ]
    if len(candidates) < min_materials:
        lines.append(
            f"**Внимание:** в заданном диапазоне найдено {len(candidates)} материалов "
            f"(запрошено не менее {min_materials}). Рассмотрите расширение периода или запуск сбора."
        )
        lines.append("")

    for i, c in enumerate(candidates[: min(len(candidates), min_materials * 2)], start=1):
        lines.extend(
            [
                f"### {i}.",
                f"**Источник** — {c['source']} ({c['country_ru']})",
                f"**Заголовок** — {c['title']}",
                "**Суть** — см. summary в ленте (требуется LLM для развёрнутого разбора).",
                f"**Контекст** — публикация от {c.get('published_at', 'дата неизвестна')}.",
                f"**Цитата** — «{c['title']}»",
                f"**Ссылка** — {c['url']}",
                "",
            ]
        )
    return "\n".join(lines)


def generate_digest(
    db: Session,
    *,
    topics: str,
    date_from: date,
    date_to: date,
    country_codes: list[str] | None,
    min_materials: int = 10,
) -> tuple[str, int, int]:
    candidates = _collect_candidates(
        db,
        date_from=date_from,
        date_to=date_to,
        country_codes=country_codes,
        topics=topics,
    )

    user_payload = {
        "topics": topics,
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "min_materials": min_materials,
        "candidates": candidates,
        "instruction": (
            "Собери дайджест только из candidates. Не используй внешние знания о статьях."
        ),
    }

    if settings.openai_api_key:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": DIGEST_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            temperature=0.2,
        )
        content = response.choices[0].message.content or ""
    else:
        content = _fallback_digest(
            topics=topics,
            date_from=date_from,
            date_to=date_to,
            candidates=candidates,
            min_materials=min_materials,
        )

    run = DigestRun(
        topics=topics,
        date_from=datetime.combine(date_from, time.min),
        date_to=datetime.combine(date_to, time.max),
        country_codes=",".join(country_codes) if country_codes else None,
        content_markdown=content,
        article_count=len(candidates),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    return content, run.id, len(candidates)

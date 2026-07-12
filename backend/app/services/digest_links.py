"""Гарантирует наличие прямых URL в каждом блоке дайджеста."""

from __future__ import annotations

import re

_BLOCK_SPLIT = re.compile(r"(?=^###\s+\d+\.)", re.MULTILINE)
_LINK_LINE = re.compile(r"\*\*Ссылка\*\*\s*[—\-:]\s*(https?://\S+)", re.IGNORECASE | re.MULTILINE)
_ID_LINE = re.compile(r"\*\*ID(?:\s+кандидата)?\*\*\s*[—\-:]\s*(\d+)", re.IGNORECASE)
_TITLE_LINE = re.compile(r"\*\*Заголовок\*\*\s*[—\-:]\s*(.+)", re.IGNORECASE | re.MULTILINE)
_SOURCE_LINE = re.compile(r"\*\*Источник\*\*\s*[—\-:]\s*(.+)", re.IGNORECASE | re.MULTILINE)


def _normalize_title(value: str) -> str:
    return value.strip().strip("«»\"'").lower()


def _find_url_for_block(block: str, by_id: dict[int, str], by_title: dict[str, str]) -> str | None:
    id_match = _ID_LINE.search(block)
    if id_match:
        url = by_id.get(int(id_match.group(1)))
        if url:
            return url

    title_match = _TITLE_LINE.search(block)
    if title_match:
        title = _normalize_title(title_match.group(1))
        if title in by_title:
            return by_title[title]
        for candidate_title, url in by_title.items():
            if candidate_title in title or title in candidate_title:
                return url

    source_match = _SOURCE_LINE.search(block)
    if source_match:
        source_text = source_match.group(1).lower()
        for candidate_title, url in by_title.items():
            if candidate_title[:40] in source_text:
                return url

    return None


def _format_link_line(url: str) -> str:
    # Markdown-ссылка: полный URL виден в тексте и кликабелен в UI
    return f"**Ссылка** — [{url}]({url})"


def ensure_digest_links(content: str, candidates: list[dict]) -> str:
    """Добавляет или исправляет строку **Ссылка** в каждом нумерованном блоке."""
    if not candidates:
        return content

    by_id = {int(c["id"]): c["url"] for c in candidates if c.get("id") and c.get("url")}
    by_title = {
        _normalize_title(c["title"]): c["url"]
        for c in candidates
        if c.get("title") and c.get("url")
    }

    parts = _BLOCK_SPLIT.split(content)
    if len(parts) <= 1:
        return content

    fixed: list[str] = []
    missing_urls: list[str] = []

    for part in parts:
        if not part.strip():
            continue
        if not part.lstrip().startswith("###"):
            fixed.append(part)
            continue

        link_match = _LINK_LINE.search(part)
        if link_match:
            url = link_match.group(1).rstrip(").,;]")
            part = _LINK_LINE.sub(_format_link_line(url), part, count=1)
            fixed.append(part)
            continue

        url = _find_url_for_block(part, by_id, by_title)
        if url:
            fixed.append(part.rstrip() + f"\n{_format_link_line(url)}\n")
        else:
            fixed.append(part)
            header = part.split("\n", 1)[0].strip()
            missing_urls.append(header)

    result = "".join(fixed)

    if missing_urls:
        result += (
            "\n\n---\n\n"
            "> **Примечание:** для части блоков URL восстановлен из реестра; "
            "проверьте соответствие заголовков.\n"
        )

    return result


def count_link_lines(content: str) -> int:
    return len(_LINK_LINE.findall(content))

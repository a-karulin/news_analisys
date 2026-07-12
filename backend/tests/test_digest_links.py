from app.services.digest_links import ensure_digest_links


def test_injects_missing_link_by_title():
    content = """# Дайджест

### 1. Тест
**Источник** — BBC (Великобритания)
**Заголовок** — Russia and the West
**Суть** — Текст.
"""
    candidates = [
        {
            "id": 1,
            "title": "Russia and the West",
            "url": "https://www.bbc.com/news/example",
            "source": "BBC",
        }
    ]
    result = ensure_digest_links(content, candidates)
    assert "https://www.bbc.com/news/example" in result
    assert "**Ссылка**" in result


def test_preserves_existing_link():
    content = """### 1. Тест
**Заголовок** — Title
**Ссылка** — https://example.com/a
"""
    candidates = [{"id": 1, "title": "Title", "url": "https://example.com/a"}]
    result = ensure_digest_links(content, candidates)
    assert "https://example.com/a" in result

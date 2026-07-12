"""Клиент локального Ollama (http://localhost:11434)."""

from __future__ import annotations

import httpx

from app.config import settings


class OllamaError(RuntimeError):
    pass


def _base_url() -> str:
    return settings.ollama_base_url.rstrip("/")


def is_available() -> bool:
    try:
        with httpx.Client(timeout=settings.ollama_probe_timeout_sec) as client:
            response = client.get(f"{_base_url()}/api/tags")
            return response.status_code == 200
    except httpx.HTTPError:
        return False


def list_models() -> list[str]:
    try:
        with httpx.Client(timeout=settings.ollama_probe_timeout_sec) as client:
            response = client.get(f"{_base_url()}/api/tags")
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", []) if m.get("name")]
    except httpx.HTTPError:
        return []


def complete_chat(*, system: str, user: str, temperature: float | None = None) -> str:
    if not is_available():
        raise OllamaError(
            f"Ollama недоступна по адресу {_base_url()}. "
            "Установите Ollama и запустите: ollama serve && ollama pull "
            f"{settings.ollama_model}"
        )

    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {
            "temperature": temperature if temperature is not None else settings.ollama_temperature,
            "num_predict": settings.ollama_max_tokens,
        },
    }

    with httpx.Client(timeout=settings.ollama_timeout_sec) as client:
        response = client.post(f"{_base_url()}/api/chat", json=payload)

    if response.status_code >= 400:
        detail = response.text[:500]
        raise OllamaError(f"Ollama HTTP {response.status_code}: {detail}")

    data = response.json()
    try:
        return data["message"]["content"]
    except (KeyError, TypeError) as exc:
        raise OllamaError(f"Неожиданный ответ Ollama: {data!r}") from exc

"""Выбор и вызов LLM: YandexGPT, локальный Ollama, черновой fallback."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.config import settings
from app.services import ollama, yandex_gpt

LLMProviderId = Literal["auto", "yandex", "ollama", "fallback"]
ResolvedProvider = Literal["yandex", "ollama", "fallback"]


class LLMError(RuntimeError):
    pass


@dataclass
class ProviderStatus:
    id: str
    name: str
    available: bool
    model: str | None
    hint: str | None


def list_providers() -> list[ProviderStatus]:
    yandex_ok = settings.yandex_configured
    ollama_ok = ollama.is_available()
    ollama_models = ollama.list_models() if ollama_ok else []

    return [
        ProviderStatus(
            id="auto",
            name="Авто (YandexGPT → Ollama → черновик)",
            available=True,
            model=None,
            hint="YandexGPT, если есть ключ; иначе локальный Ollama; иначе сводка без LLM.",
        ),
        ProviderStatus(
            id="yandex",
            name="YandexGPT (облако)",
            available=yandex_ok,
            model=(
                f"gpt://{settings.yandex_folder_id}/{settings.yandex_model}/"
                f"{settings.yandex_model_version}"
                if yandex_ok
                else None
            ),
            hint=(
                "Задайте YANDEX_FOLDER_ID и YANDEX_API_KEY в backend/.env"
                if not yandex_ok
                else None
            ),
        ),
        ProviderStatus(
            id="ollama",
            name="Ollama (локально)",
            available=ollama_ok,
            model=settings.ollama_model if ollama_ok else None,
            hint=(
                f"Установите Ollama и выполните: ollama pull {settings.ollama_model}"
                if not ollama_ok
                else (
                    f"Модели: {', '.join(ollama_models[:5])}"
                    if ollama_models
                    else None
                )
            ),
        ),
    ]


def resolve_provider(requested: LLMProviderId) -> ResolvedProvider:
    if requested == "auto":
        if settings.yandex_configured:
            return "yandex"
        if ollama.is_available():
            return "ollama"
        return "fallback"

    if requested == "yandex":
        if not settings.yandex_configured:
            raise LLMError(
                "YandexGPT не настроен. Задайте YANDEX_FOLDER_ID и YANDEX_API_KEY в .env "
                "или выберите «Ollama (локально)» / «Авто»."
            )
        return "yandex"

    if requested == "ollama":
        if not ollama.is_available():
            raise LLMError(
                f"Ollama недоступна ({settings.ollama_base_url}). "
                f"См. раздел «Локальный ИИ» в README."
            )
        return "ollama"

    if requested == "fallback":
        return "fallback"

    raise LLMError(f"Неизвестный провайдер: {requested}")


def complete_chat(
    *,
    system: str,
    user: str,
    provider: LLMProviderId = "auto",
    temperature: float | None = None,
) -> tuple[str, ResolvedProvider]:
    resolved = resolve_provider(provider)

    if resolved == "yandex":
        text = yandex_gpt.complete_chat(system=system, user=user, temperature=temperature)
        return text, "yandex"

    if resolved == "ollama":
        text = ollama.complete_chat(system=system, user=user, temperature=temperature)
        return text, "ollama"

    raise LLMError("Провайдер fallback не вызывает LLM — используйте build_fallback_digest.")

"""Клиент YandexGPT (Yandex Cloud Foundation Models, REST)."""

from __future__ import annotations

import httpx

from app.config import settings

YANDEX_COMPLETION_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"


class YandexGPTError(RuntimeError):
    pass


def _auth_headers() -> dict[str, str]:
    if settings.yandex_api_key:
        return {"Authorization": f"Api-Key {settings.yandex_api_key}"}
    if settings.yandex_iam_token:
        return {"Authorization": f"Bearer {settings.yandex_iam_token}"}
    raise YandexGPTError(
        "Задайте YANDEX_API_KEY или YANDEX_IAM_TOKEN в .env (см. Yandex Cloud → Foundation Models)."
    )


def model_uri() -> str:
    if not settings.yandex_folder_id:
        raise YandexGPTError("Задайте YANDEX_FOLDER_ID (ID каталога в Yandex Cloud).")
    version = settings.yandex_model_version.strip("/")
    model = settings.yandex_model.strip("/")
    return f"gpt://{settings.yandex_folder_id}/{model}/{version}"


def is_configured() -> bool:
    has_auth = bool(settings.yandex_api_key or settings.yandex_iam_token)
    return bool(settings.yandex_folder_id and has_auth)


def complete_chat(*, system: str, user: str, temperature: float | None = None) -> str:
    """Синхронный запрос completion с ролями system + user."""
    headers = {
        "Content-Type": "application/json",
        **_auth_headers(),
    }
    if settings.yandex_folder_id:
        headers["x-folder-id"] = settings.yandex_folder_id

    payload = {
        "modelUri": model_uri(),
        "completionOptions": {
            "stream": False,
            "temperature": temperature if temperature is not None else settings.yandex_temperature,
            "maxTokens": str(settings.yandex_max_tokens),
        },
        "messages": [
            {"role": "system", "text": system},
            {"role": "user", "text": user},
        ],
    }

    with httpx.Client(timeout=settings.yandex_timeout_sec) as client:
        response = client.post(YANDEX_COMPLETION_URL, headers=headers, json=payload)

    if response.status_code >= 400:
        detail = response.text[:500]
        raise YandexGPTError(f"YandexGPT HTTP {response.status_code}: {detail}")

    data = response.json()
    try:
        return data["result"]["alternatives"][0]["message"]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise YandexGPTError(f"Неожиданный ответ YandexGPT: {data!r}") from exc

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./news_analysis.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    ingest_user_agent: str = (
        "NewsAnalysisBot/1.0 (+https://github.com/local/news-analysis; research aggregator)"
    )

    # YandexGPT (Yandex Cloud Foundation Models)
    yandex_folder_id: str | None = None
    yandex_api_key: str | None = None
    yandex_iam_token: str | None = None
    yandex_model: str = "yandexgpt"
    yandex_model_version: str = "latest"
    yandex_temperature: float = 0.2
    yandex_max_tokens: int = 8000
    yandex_timeout_sec: float = 120.0

    # Локальный Ollama (fallback без облачного ключа)
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:7b"
    ollama_temperature: float = 0.2
    ollama_max_tokens: int = 8000
    ollama_timeout_sec: float = 300.0
    ollama_probe_timeout_sec: float = 3.0

    # Провайдер по умолчанию: auto | yandex | ollama
    llm_default_provider: str = "auto"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def yandex_configured(self) -> bool:
        has_auth = bool(self.yandex_api_key or self.yandex_iam_token)
        return bool(self.yandex_folder_id and has_auth)


settings = Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./news_analysis.db"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    ingest_user_agent: str = (
        "NewsAnalysisBot/1.0 (+https://github.com/local/news-analysis; research aggregator)"
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()

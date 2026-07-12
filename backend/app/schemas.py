from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

LLMProviderChoice = Literal["auto", "yandex", "ollama"]


class CountryOut(BaseModel):
    id: int
    code: str
    name_ru: str
    name_en: str

    model_config = {"from_attributes": True}


class NewsSourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    base_url: str = Field(min_length=4, max_length=512)
    rss_url: str | None = Field(default=None, max_length=512)
    country_code: str = Field(min_length=2, max_length=8)
    is_active: bool = True


class NewsSourceUpdate(BaseModel):
    name: str | None = None
    base_url: str | None = None
    rss_url: str | None = None
    country_code: str | None = None
    is_active: bool | None = None


class NewsSourceOut(BaseModel):
    id: int
    name: str
    base_url: str
    rss_url: str | None
    country_id: int
    is_active: bool
    created_at: datetime
    country: CountryOut

    model_config = {"from_attributes": True}


class ArticleOut(BaseModel):
    id: int
    source_id: int
    title: str
    url: str
    summary: str | None
    published_at: datetime | None
    language: str | None
    fetched_at: datetime
    source_name: str
    country_code: str
    country_name_ru: str

    model_config = {"from_attributes": True}


class ArticleListResponse(BaseModel):
    items: list[ArticleOut]
    total: int
    page: int
    page_size: int


class IngestResponse(BaseModel):
    sources_processed: int
    articles_added: int
    articles_updated: int
    errors: list[str]


class LLMProviderOut(BaseModel):
    id: str
    name: str
    available: bool
    model: str | None
    hint: str | None


class DigestRequest(BaseModel):
    topics: str = Field(
        description="Темы дайджеста через запятую или свободный текст",
        min_length=3,
    )
    date_from: date
    date_to: date
    country_codes: list[str] | None = Field(
        default=None,
        description="Фильтр по кодам стран (US, UK, …). Пусто — все активные источники.",
    )
    min_materials: int = Field(default=10, ge=1, le=50)
    llm_provider: LLMProviderChoice = Field(
        default="auto",
        description="auto — YandexGPT при наличии ключа, иначе Ollama; yandex | ollama — явный выбор",
    )


class DigestResponse(BaseModel):
    id: int
    content_markdown: str
    article_count: int
    candidates_used: int
    llm_provider: str
    created_at: datetime

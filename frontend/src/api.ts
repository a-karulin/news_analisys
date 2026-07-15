export type Country = {
  id: number;
  code: string;
  name_ru: string;
  name_en: string;
};

export type NewsSource = {
  id: number;
  name: string;
  base_url: string;
  rss_url: string | null;
  country_id: number;
  is_active: boolean;
  created_at: string;
  country: Country;
};

export type Article = {
  id: number;
  source_id: number;
  title: string;
  url: string;
  summary: string | null;
  published_at: string | null;
  language: string | null;
  fetched_at: string;
  source_name: string;
  country_code: string;
  country_name_ru: string;
};

export type ArticleListResponse = {
  items: Article[];
  total: number;
  page: number;
  page_size: number;
};

export type LLMProvider = {
  id: string;
  name: string;
  available: boolean;
  model: string | null;
  hint: string | null;
};

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${path}`;

  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  countries: () => request<Country[]>("/api/countries"),
  sources: (params: URLSearchParams) =>
    request<NewsSource[]>(`/api/sources?${params}`),
  createSource: (body: unknown) =>
    request<NewsSource>("/api/sources", { method: "POST", body: JSON.stringify(body) }),
  articles: (params: URLSearchParams) =>
    request<ArticleListResponse>(`/api/articles?${params}`),
  ingest: () =>
    request<{ sources_processed: number; articles_added: number; articles_updated: number; errors: string[] }>(
      "/api/articles/ingest",
      { method: "POST" },
    ),
  llmProviders: () => request<LLMProvider[]>("/api/llm/providers"),
  generateDigest: (body: unknown) =>
    request<{
      id: number;
      content_markdown: string;
      article_count: number;
      candidates_used: number;
      llm_provider: string;
    }>("/api/digests/generate", { method: "POST", body: JSON.stringify(body) }),
};

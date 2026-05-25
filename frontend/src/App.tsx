import { FormEvent, useCallback, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { api, Article, Country, NewsSource } from "./api";

type Tab = "sources" | "registry" | "digest";

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

export default function App() {
  const [tab, setTab] = useState<Tab>("registry");
  const [countries, setCountries] = useState<Country[]>([]);
  const [message, setMessage] = useState<{ type: "ok" | "error"; text: string } | null>(null);

  useEffect(() => {
    api.countries().then(setCountries).catch((e) => setMessage({ type: "error", text: String(e) }));
  }, []);

  return (
    <div>
      <h1>News Analysis</h1>
      <p className="subtitle">
        Сбор новостей по странам, реестр с фильтрами и редакционный дайджест прессы
      </p>

      <nav className="tabs">
        {(
          [
            ["registry", "Реестр новостей"],
            ["sources", "Источники СМИ"],
            ["digest", "Дайджест"],
          ] as const
        ).map(([id, label]) => (
          <button key={id} type="button" className={tab === id ? "active" : ""} onClick={() => setTab(id)}>
            {label}
          </button>
        ))}
      </nav>

      {message && <div className={`message ${message.type}`}>{message.text}</div>}

      {tab === "sources" && (
        <SourcesPanel countries={countries} onMessage={setMessage} />
      )}
      {tab === "registry" && (
        <RegistryPanel countries={countries} onMessage={setMessage} />
      )}
      {tab === "digest" && <DigestPanel countries={countries} onMessage={setMessage} />}
    </div>
  );
}

function SourcesPanel({
  countries,
  onMessage,
}: {
  countries: Country[];
  onMessage: (m: { type: "ok" | "error"; text: string } | null) => void;
}) {
  const [sources, setSources] = useState<NewsSource[]>([]);
  const [countryFilter, setCountryFilter] = useState("");
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState("name");
  const [sortOrder, setSortOrder] = useState("asc");
  const [name, setName] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [rssUrl, setRssUrl] = useState("");
  const [countryCode, setCountryCode] = useState("US");

  const load = useCallback(() => {
    const p = new URLSearchParams();
    if (countryFilter) p.set("country_code", countryFilter);
    if (search) p.set("search", search);
    p.set("sort_by", sortBy);
    p.set("sort_order", sortOrder);
    api.sources(p).then(setSources).catch((e) => onMessage({ type: "error", text: String(e) }));
  }, [countryFilter, search, sortBy, sortOrder, onMessage]);

  useEffect(() => {
    load();
  }, [load]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    try {
      await api.createSource({
        name,
        base_url: baseUrl,
        rss_url: rssUrl || null,
        country_code: countryCode,
        is_active: true,
      });
      onMessage({ type: "ok", text: "Источник добавлен" });
      setName("");
      setBaseUrl("");
      setRssUrl("");
      load();
    } catch (err) {
      onMessage({ type: "error", text: String(err) });
    }
  }

  return (
    <div className="panel">
      <h2 style={{ marginTop: 0 }}>Добавить источник</h2>
      <form className="form-grid" onSubmit={onSubmit}>
        <label>
          Название СМИ
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label>
          URL сайта
          <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} required placeholder="https://..." />
        </label>
        <label>
          RSS (рекомендуется для сбора)
          <input value={rssUrl} onChange={(e) => setRssUrl(e.target.value)} placeholder="https://.../feed" />
        </label>
        <label>
          Страна
          <select value={countryCode} onChange={(e) => setCountryCode(e.target.value)}>
            {countries.map((c) => (
              <option key={c.code} value={c.code}>
                {c.name_ru} ({c.code})
              </option>
            ))}
          </select>
        </label>
        <button type="submit" className="primary">
          Добавить
        </button>
      </form>

      <h2>Реестр источников</h2>
      <div className="filters">
        <label>
          Страна
          <select value={countryFilter} onChange={(e) => setCountryFilter(e.target.value)}>
            <option value="">Все</option>
            {countries.map((c) => (
              <option key={c.code} value={c.code}>
                {c.name_ru}
              </option>
            ))}
          </select>
        </label>
        <label>
          Поиск
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="название или URL" />
        </label>
        <label>
          Сортировка
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
            <option value="name">Название</option>
            <option value="country">Страна</option>
            <option value="created_at">Дата добавления</option>
            <option value="base_url">URL</option>
          </select>
        </label>
        <label>
          Порядок
          <select value={sortOrder} onChange={(e) => setSortOrder(e.target.value)}>
            <option value="asc">По возрастанию</option>
            <option value="desc">По убыванию</option>
          </select>
        </label>
      </div>

      <table>
        <thead>
          <tr>
            <th>СМИ</th>
            <th>Страна</th>
            <th>RSS</th>
            <th>Сайт</th>
          </tr>
        </thead>
        <tbody>
          {sources.map((s) => (
            <tr key={s.id}>
              <td>
                {s.name}{" "}
                <span className={`badge ${s.is_active ? "" : "off"}`}>
                  {s.is_active ? "активен" : "выкл"}
                </span>
              </td>
              <td>{s.country.name_ru}</td>
              <td>{s.rss_url ? "да" : "—"}</td>
              <td>
                <a href={s.base_url} target="_blank" rel="noreferrer">
                  {s.base_url}
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RegistryPanel({
  countries,
  onMessage,
}: {
  countries: Country[];
  onMessage: (m: { type: "ok" | "error"; text: string } | null) => void;
}) {
  const [articles, setArticles] = useState<Article[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [dateFrom, setDateFrom] = useState(todayIso());
  const [dateTo, setDateTo] = useState(todayIso());
  const [countryCodes, setCountryCodes] = useState("");
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState("published_at");
  const [sortOrder, setSortOrder] = useState("desc");
  const [ingesting, setIngesting] = useState(false);

  const load = useCallback(() => {
    const p = new URLSearchParams();
    if (dateFrom) p.set("date_from", dateFrom);
    if (dateTo) p.set("date_to", dateTo);
    if (countryCodes) p.set("country_codes", countryCodes);
    if (search) p.set("search", search);
    p.set("sort_by", sortBy);
    p.set("sort_order", sortOrder);
    p.set("page", String(page));
    p.set("page_size", "30");
    api
      .articles(p)
      .then((r) => {
        setArticles(r.items);
        setTotal(r.total);
      })
      .catch((e) => onMessage({ type: "error", text: String(e) }));
  }, [dateFrom, dateTo, countryCodes, search, sortBy, sortOrder, page, onMessage]);

  useEffect(() => {
    load();
  }, [load]);

  async function runIngest() {
    setIngesting(true);
    onMessage(null);
    try {
      const r = await api.ingest();
      onMessage({
        type: "ok",
        text: `Сбор: +${r.articles_added} новых, обновлено ${r.articles_updated}. Ошибок: ${r.errors.length}`,
      });
      load();
    } catch (e) {
      onMessage({ type: "error", text: String(e) });
    } finally {
      setIngesting(false);
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / 30));

  return (
    <div className="panel">
      <div className="filters">
        <label>
          Дата с
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
        </label>
        <label>
          Дата по
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        </label>
        <label>
          Страны (коды через запятую)
          <input
            value={countryCodes}
            onChange={(e) => setCountryCodes(e.target.value)}
            placeholder="US,UK,DE"
          />
        </label>
        <label>
          Поиск в заголовке/summary
          <input value={search} onChange={(e) => setSearch(e.target.value)} />
        </label>
        <label>
          Сортировка
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
            <option value="published_at">Дата публикации</option>
            <option value="title">Заголовок</option>
            <option value="source">Источник</option>
            <option value="country">Страна</option>
            <option value="fetched_at">Дата загрузки</option>
          </select>
        </label>
        <label>
          Порядок
          <select value={sortOrder} onChange={(e) => setSortOrder(e.target.value)}>
            <option value="desc">Новые сверху</option>
            <option value="asc">Старые сверху</option>
          </select>
        </label>
      </div>

      <div className="actions">
        <button type="button" className="primary" onClick={runIngest} disabled={ingesting}>
          {ingesting ? "Сбор…" : "Собрать новости (RSS)"}
        </button>
        <button type="button" className="secondary" onClick={() => { setPage(1); load(); }}>
          Обновить список
        </button>
      </div>

      <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
        Найдено: {total}. Для платных СМИ без RSS добавьте ленту вручную во вкладке «Источники».
      </p>

      <table>
        <thead>
          <tr>
            <th>Дата</th>
            <th>Источник</th>
            <th>Страна</th>
            <th>Заголовок</th>
          </tr>
        </thead>
        <tbody>
          {articles.map((a) => (
            <tr key={a.id}>
              <td>{a.published_at ? a.published_at.slice(0, 10) : "—"}</td>
              <td>{a.source_name}</td>
              <td>{a.country_name_ru}</td>
              <td>
                <a href={a.url} target="_blank" rel="noreferrer">
                  {a.title}
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="pagination">
        <button type="button" className="secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
          ←
        </button>
        <span>
          Стр. {page} / {totalPages}
        </span>
        <button
          type="button"
          className="secondary"
          disabled={page >= totalPages}
          onClick={() => setPage((p) => p + 1)}
        >
          →
        </button>
      </div>
    </div>
  );
}

function DigestPanel({
  countries,
  onMessage,
}: {
  countries: Country[];
  onMessage: (m: { type: "ok" | "error"; text: string } | null) => void;
}) {
  const [topics, setTopics] = useState(
    "Россия, европейская и американская политика, санкции, энергетика",
  );
  const [dateFrom, setDateFrom] = useState(todayIso());
  const [dateTo, setDateTo] = useState(todayIso());
  const [countryCodes, setCountryCodes] = useState<string[]>([]);
  const [minMaterials, setMinMaterials] = useState(10);
  const [markdown, setMarkdown] = useState("");
  const [loading, setLoading] = useState(false);

  function toggleCountry(code: string) {
    setCountryCodes((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code],
    );
  }

  async function generate() {
    setLoading(true);
    onMessage(null);
    try {
      const r = await api.generateDigest({
        topics,
        date_from: dateFrom,
        date_to: dateTo,
        country_codes: countryCodes.length ? countryCodes : null,
        min_materials: minMaterials,
      });
      setMarkdown(r.content_markdown);
      onMessage({
        type: "ok",
        text: `Дайджест #${r.id}: кандидатов в выборке ${r.candidates_used}`,
      });
    } catch (e) {
      onMessage({ type: "error", text: String(e) });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panel">
      <p style={{ color: "var(--muted)", fontSize: "0.9rem" }}>
        Дайджест строится только из материалов в реестре за указанные даты. LLM следует редакционным
        правилам (без выдуманных цитат и ссылок). Задайте OPENAI_API_KEY для полноценного разбора.
      </p>

      <div className="filters">
        <label style={{ gridColumn: "1 / -1" }}>
          Темы
          <textarea value={topics} onChange={(e) => setTopics(e.target.value)} />
        </label>
        <label>
          Дата с
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
        </label>
        <label>
          Дата по
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        </label>
        <label>
          Мин. материалов
          <input
            type="number"
            min={1}
            max={50}
            value={minMaterials}
            onChange={(e) => setMinMaterials(Number(e.target.value))}
          />
        </label>
      </div>

      <fieldset style={{ border: "none", padding: 0, margin: "0 0 1rem" }}>
        <legend style={{ color: "var(--muted)", fontSize: "0.8rem" }}>Страны (пусто = все)</legend>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
          {countries.map((c) => (
            <label key={c.code} style={{ flexDirection: "row", alignItems: "center", gap: "0.35rem" }}>
              <input
                type="checkbox"
                checked={countryCodes.includes(c.code)}
                onChange={() => toggleCountry(c.code)}
              />
              {c.name_ru}
            </label>
          ))}
        </div>
      </fieldset>

      <div className="actions">
        <button type="button" className="primary" onClick={generate} disabled={loading}>
          {loading ? "Генерация…" : "Сформировать дайджест"}
        </button>
      </div>

      {markdown && (
        <div className="digest-output">
          <ReactMarkdown>{markdown}</ReactMarkdown>
        </div>
      )}
    </div>
  );
}

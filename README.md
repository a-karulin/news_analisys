# News Analysis

Агрегатор международных новостей с разбивкой источников по странам, реестром с фильтрацией и генерацией **редакционного дайджеста прессы** по заданным темам и строгому диапазону дат.

**База данных:** PostgreSQL.

## Возможности

- **50+ источников** (США, Великобритания, ЕС, Азия и др.) с привязкой к стране
- **UI**: добавление СМИ, реестр с фильтрами и сортировкой
- **Сбор** через RSS-ленты
- **Дайджест**: YandexGPT, Ollama (локально) или авто-режим

---

## Установка и запуск на macOS

### 1. Зависимости системы

```bash
# Homebrew (если ещё нет): https://brew.sh
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

brew install python@3.12 node docker
```

Для локального PostgreSQL без Docker (вариант B ниже):

```bash
brew install postgresql@16
```

### 2. PostgreSQL

#### Вариант A — Docker (рекомендуется)

```bash
cd /path/to/news_analysis
docker compose up -d
docker compose ps   # STATUS: healthy
```

Параметры по умолчанию:
- хост: `127.0.0.1:5432`
- БД: `news_analysis`
- пользователь / пароль: `news` / `news`

#### Вариант B — PostgreSQL через Homebrew

```bash
brew services start postgresql@16

# Создание пользователя и базы (один раз)
psql postgres <<'SQL'
CREATE USER news WITH PASSWORD 'news' CREATEDB;
CREATE DATABASE news_analysis OWNER news;
SQL
```

Проверка:

```bash
psql postgresql://news:news@127.0.0.1:5432/news_analysis -c "SELECT version();"
```

### 3. Backend

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# при необходимости отредактируйте DATABASE_URL и ключи Yandex/Ollama

uvicorn app.main:app --reload --port 8000
```

При первом запуске автоматически:
- создаются таблицы в PostgreSQL;
- загружаются страны и источники (seed).

Проверка:

```bash
curl http://127.0.0.1:8000/api/health
# ожидается: "database": "postgresql", "database_connected": true
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Откройте http://localhost:5173

### 5. (Опционально) Ollama — локальный ИИ

```bash
brew install ollama
ollama serve          # отдельный терминал
ollama pull qwen2.5:7b
```

В `backend/.env` уже задано `OLLAMA_MODEL=qwen2.5:7b`.

---

## Перенос данных из SQLite

Если раньше использовалась SQLite-база `backend/news_analysis.db`:

```bash
cd backend
source .venv/bin/activate
# PostgreSQL должен быть запущен
python scripts/migrate_sqlite_to_postgres.py --sqlite ./news_analysis.db
```

---

## Переменные окружения (`backend/.env`)

| Переменная | Пример | Описание |
|------------|--------|----------|
| `DATABASE_URL` | `postgresql+psycopg://news:news@127.0.0.1:5432/news_analysis` | Подключение к PostgreSQL |
| `YANDEX_FOLDER_ID` | `b1g...` | Каталог Yandex Cloud |
| `YANDEX_API_KEY` | `AQVN...` | API-ключ YandexGPT |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Локальная модель |
| `LLM_DEFAULT_PROVIDER` | `auto` | `auto` / `yandex` / `ollama` |

---

## Рабочий процесс

1. **Реестр новостей** → «Собрать новости (RSS)».
2. Задайте период и страны.
3. **Дайджест** → темы → выберите ИИ → «Сформировать дайджест».

---

## Остановка сервисов

```bash
# PostgreSQL (Docker)
docker compose down

# PostgreSQL (Homebrew)
brew services stop postgresql@16
```

---

## Структура

```
backend/app/          — FastAPI, PostgreSQL, ingest, digest
frontend/src/         — React UI
docker-compose.yml    — PostgreSQL для разработки
```

## API

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/health` | Статус БД и ИИ |
| GET | `/api/countries` | Страны |
| GET/POST | `/api/sources` | Источники |
| GET | `/api/articles` | Реестр |
| POST | `/api/articles/ingest` | Сбор RSS |
| GET | `/api/llm/providers` | Доступные ИИ |
| POST | `/api/digests/generate` | Дайджест |

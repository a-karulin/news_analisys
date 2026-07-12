# News Analysis

Агрегатор международных новостей с разбивкой источников по странам, реестром с фильтрацией и генерацией **редакционного дайджеста прессы** по заданным темам и строгому диапазону дат.

## Возможности

- **50+ источников** из вашего списка (США, Великобритания, ЕС, Азия, Ближний Восток, Африка и др.) с привязкой к стране
- **UI**: добавление СМИ (название, URL, RSS, страна)
- **Реестр новостей**: фильтр по датам, странам, поиск; сортировка по дате, заголовку, источнику, стране
- **Сбор** через публичные RSS-ленты (где они указаны в seed)
- **Дайджест**: LLM формирует блоки «Источник / Заголовок / Суть / Контекст / Цитата / Ссылка» с запретом на выдуманные данные (см. промпт в `backend/app/services/digest.py`)

## Требования

- Python 3.11+
- Node.js 18+
- **YandexGPT** (облако, опционально) или **Ollama** (локально, бесплатно)

## Запуск

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # YANDEX_FOLDER_ID, YANDEX_API_KEY
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Откройте http://localhost:5173

## Рабочий процесс

1. Вкладка **«Реестр новостей»** → **«Собрать новости (RSS)»** — загрузка статей в БД.
2. Отфильтруйте период (например 14–16.05.2026) и страны.
3. Вкладка **«Дайджест»** — укажите темы, те же даты, нажмите **«Сформировать дайджест»**.

Во вкладке **«Дайджест»** выберите ИИ:
- **Авто** — YandexGPT, если есть ключ; иначе локальный Ollama; иначе черновик без LLM.
- **YandexGPT** — только облако.
- **Ollama** — только локальная модель.

Проверка: `GET http://127.0.0.1:8000/api/llm/providers` или `/api/health`.

### YandexGPT (облако)

1. [Yandex Cloud](https://console.yandex.cloud/) → каталог → **ID каталога** → `YANDEX_FOLDER_ID`.
2. Сервисный аккаунт с ролью `ai.languageModels.user` → **API-ключ** → `YANDEX_API_KEY`.
3. (Опционально) `YANDEX_MODEL=yandexgpt-lite` для более быстрых ответов.

Документация: [Foundation Models — YandexGPT](https://yandex.cloud/ru/docs/foundation-models/).

### Локальный ИИ (Ollama)

Ollama запускает open-source модели на вашем Mac/PC без облачных ключей.

#### macOS

```bash
# 1. Установка (официальный установщик)
brew install ollama
# или скачайте с https://ollama.com/download

# 2. Запуск сервера (в отдельном терминале или как фоновый сервис)
ollama serve

# 3. Скачивание модели (рекомендуется для русского текста)
ollama pull qwen2.5:7b
# альтернативы: llama3.2, gemma2:9b, mistral

# 4. Проверка
ollama list
curl http://127.0.0.1:11434/api/tags
```

В `backend/.env` (по умолчанию уже так):

```env
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:7b
```

Перезапустите backend. В `/api/health` должно быть `"ollama_available": true`.

#### Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
ollama pull qwen2.5:7b
```

#### Windows

Скачайте установщик с [ollama.com](https://ollama.com/download), после установки в PowerShell:

```powershell
ollama pull qwen2.5:7b
```

Сервер стартует автоматически.

#### Требования к железу

| Модель | RAM (ориентир) |
|--------|----------------|
| `qwen2.5:7b` | 8 GB+ |
| `qwen2.5:14b` | 16 GB+ |
| `llama3.2:3b` | 4 GB+ (быстрее, но слабее для длинных дайджестов) |

Для дайджестов на 10+ материалов лучше **7B+** и **16 GB RAM**.

## Ограничения

- Многие платные СМИ (NYT, WSJ, FT, Economist…) **не отдают полный текст** через RSS; для них укажите рабочий RSS вручную или подключите отдельный парсер/API.
- Даты в RSS иногда в часовом поясе источника — фильтр идёт по полю `published_at` из ленты.
- Цитаты «на языке оригинала» в полном объёме возможны только если в ленте есть summary/текст; иначе LLM обязан это указать (заложено в system prompt).

## Структура

```
backend/app/          — FastAPI, SQLite, ingest, digest
frontend/src/         — React UI
```

## API (кратко)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/countries` | Страны |
| GET/POST | `/api/sources` | Источники |
| GET | `/api/articles` | Реестр (+ query-параметры фильтров) |
| POST | `/api/articles/ingest` | Сбор RSS |
| GET | `/api/llm/providers` | Доступные ИИ |
| POST | `/api/digests/generate` | Дайджест (`llm_provider`: auto/yandex/ollama) |

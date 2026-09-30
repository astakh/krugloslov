# Часть 8: LLM-клиент и инфраструктура промптов

## Реализовано

### 1. GigaChat клиент (`app/llm/client.py`)

**Двухуровневая архитектура:**

**Слой A — `chat()`:**
- Базовый HTTP-запрос к GigaChat API
- Авторизация через OAuth с управлением токеном
- Обработка HTTP-ошибок с retry-логикой:
  - 401: refresh токена + один retry
  - 429: retry с backoff (учитывает Retry-After)
  - 402: `LlmQuotaExceeded` (без retry)
  - 400: `LlmUnavailable` (без retry)
  - 5xx: `LlmUnavailable` (после retry)
- Проверка `finish_reason`:
  - `blacklist`: `LlmRefused`
  - `length`: контентная ошибка (retry в слое B)
- Параллелизм через `asyncio.Semaphore(GIGACHAT_MAX_CONCURRENCY)`

**Слой B — `chat_json()`:**
- Вызывает слой A
- Извлекает JSON из ответа (удаляет markdown-блоки)
- Парсит JSON через `json.loads`
- Валидирует через Pydantic-схему
- При ошибке парсинга/валидации — retry (до `max_retries`)
- Возвращает валидированный Pydantic-объект

**Управление токеном:**
- OAuth-запрос к `https://ngw.devices.sberbank.ru:9443/api/v2/oauth`
- Токен хранится в памяти с `expires_at`
- Обновление через `asyncio.Lock` (single-flight механизм)
- Обновление за 120 секунд до истечения
- Конкурентные запросы ожидают одного обновления

### 2. Исключения (`app/llm/exceptions.py`)

- `LlmError` — базовое исключение для всех LLM-ошибок
- `LlmUnavailable` — сервис недоступен (сеть, 400, 5xx после retry)
- `LlmQuotaExceeded` — квота исчерпана (402)
- `LlmInvalidResponse` — невалидный ответ (ошибка парсинга/валидации)
- `LlmRefused` — контент отклонён (blacklist)

### 3. PromptService (`app/services/prompt_service.py`)

- Читает промпты из таблицы `prompts`
- Если промпт не найден — использует fallback из кода
- Логирует критическую ошибку `prompt_missing` при отсутствии промпта
- Метод `format_prompt()` для подстановки плейсхолдеров

**Fallback-промпты:**
- `generate_sentences` — генерация предложений с плейсхолдерами `{level}`, `{count}`, `{word}`
- `evaluate_translation` — оценка перевода (без плейсхолдеров в системном шаблоне)

### 4. LlmLogger (`app/services/llm_logger.py`)

- Логирует каждый вызов в таблицу `llm_calls`
- Автокоммит-транзакция (не блокирует основную операцию)
- Записывает: purpose, user_id, lesson_id, exercise_id, attempt, request, response, status, http_status, latency_ms, prompt_tokens, completion_tokens

### 5. Pydantic-схемы (`app/llm/schemas.py`)

- `GenerateSentencesResponse` — ответ генерации предложений
- `EvaluateTranslationResponse` — ответ оценки перевода
- `SentencePair` — пара (english, russian)
- `WordEvaluation` — оценка слова (word, status, feedback)

### 6. Миграция (`002_add_default_prompts.py`)

- Заполняет таблицу `prompts` начальными шаблонами
- Down-миграция удаляет записи

## Ключевые особенности

### Обработка ошибок

**Транспортные ошибки (retry):**
- 401: один refresh + retry
- 429: retry с backoff (1s, 2s + jitter), учитывает Retry-After
- 5xx, timeout: retry с backoff (до 2 попыток)

**Контентные ошибки (retry в слое B):**
- `finish_reason = length`: retry
- Невалидный JSON: retry
- Ошибка валидации схемы: retry

**Критические ошибки (без retry):**
- 402: `LlmQuotaExceeded`
- 400: `LlmUnavailable`
- `finish_reason = blacklist`: `LlmRefused`

### Параллелизм

- `asyncio.Semaphore(GIGACHAT_MAX_CONCURRENCY)` — ограничение параллельных запросов
- `asyncio.Lock` для обновления токена — single-flight механизм
- Ожидание семафора входит в общий дедлайн операции

### Извлечение JSON

- Удаляет markdown-блоки (```json ... ```)
- Находит первый `{` или `[` и парный закрывающий
- Обрабатывает вложенные структуры
- Возвращает `None` если JSON не найден

### Логирование

- Каждый вызов логируется в `llm_calls` отдельной транзакцией
- При ошибке основной операции создаётся событие `llm_error`
- Не блокирует основную операцию при ошибке логирования

## Тесты

### Unit-тесты с моками (`tests/test_llm_client.py`)

**Управление токеном:**
- Обновление при истечении
- Обновление за 120 секунд до истечения
- Не обновление при валидном токене
- Конкурентное обновление (single-flight)

**Слой A (chat):**
- Успешный запрос
- 401 с retry после refresh
- 401 дважды → `LlmUnavailable`
- 402 → `LlmQuotaExceeded`
- Timeout → `LlmUnavailable`

**Слой B (chat_json):**
- Парсинг валидного JSON
- Извлечение из markdown-блока
- Retry при невалидном JSON
- `LlmRefused` при blacklist
- Retry при ошибке валидации

**Извлечение JSON:**
- JSON-объект
- JSON-массив
- Markdown-блоки
- Вложенный JSON
- Отсутствие JSON

### Тесты PromptService (`tests/test_prompt_service.py`)

- Получение из БД
- Fallback при отсутствии
- Ошибка при неизвестном ключе
- Форматирование с плейсхолдерами
- Проверка плейсхолдеров в fallback-промптах

## Запуск тестов

```bash
# Тесты клиента (с моками HTTP)
pytest tests/test_llm_client.py -v

# Тесты сервиса промптов
pytest tests/test_prompt_service.py -v
```

## Применение миграции

```bash
cd backend
alembic upgrade head
```

## Конфигурация

Переменные окружения (из `.env`):

```env
GIGACHAT_AUTH_KEY=your_auth_key
GIGACHAT_SCOPE=GIGACHAT_API_PERS
GIGACHAT_MODEL=GigaChat
GIGACHAT_CA_CERT_PATH=/path/to/cert.pem
GIGACHAT_MAX_CONCURRENCY=3
```

## Использование

```python
from app.llm import gigachat_client
from app.llm.schemas import GenerateSentencesResponse
from app.services.prompt_service import PromptService

# 1. Получить промпт
prompt_service = PromptService(session)
template = await prompt_service.get_prompt("generate_sentences")
system_prompt = prompt_service.format_prompt(
    template,
    level="A2",
    count=3,
    word="run"
)

# 2. Подготовить сообщения
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": "Generate sentences"}
]

# 3. Вызвать LLM
result = await gigachat_client.chat_json(
    messages=messages,
    validator=GenerateSentencesResponse,
    temperature=0.7,
    max_tokens=500,
    timeout=25.0,
    max_retries=2
)

# result — валидированный Pydantic-объект
for sentence in result.sentences:
    print(f"{sentence.english} → {sentence.russian}")
```

## Критерии приёмки

✅ Есть клиент, который можно вызвать из сервисов  
✅ Токен обновляется через lock (single-flight)  
✅ Все вызовы логируются в `llm_calls`  
✅ Ошибки преобразуются в доменные исключения  
✅ Промпты читаются из БД  
✅ Есть резервные промпты, если записи нет  
✅ Тесты используют моки GigaChat, а не реальные HTTP-вызовы  
✅ Параллелизм через semaphore  
✅ Обработка 401, 429, 402, 5xx, 400  
✅ Обработка finish_reason (blacklist, length)  
✅ Извлечение JSON из markdown-блоков  
✅ Валидация через Pydantic  
✅ Retry-логика для контентных и транспортных ошибок  
✅ Миграция заполняет таблицу prompts начальными значениями

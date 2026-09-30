# Инструкция по проверке Части 8 — LLM-клиент и промпты

## Обзор

Реализован слой работы с GigaChat API с двухуровневой архитектурой:
- **Слой A**: `chat()` — базовый HTTP-запрос с обработкой ошибок
- **Слой B**: `chat_json()` — запрос с парсингом JSON и валидацией схемы

## Структура

```
backend/app/llm/
├── __init__.py           # Экспорт модуля
├── client.py             # GigaChatClient с авторизацией и retry
├── exceptions.py         # LLM-исключения
└── schemas.py            # Pydantic-схемы для валидации ответов

backend/app/services/
├── prompt_service.py     # Сервис для работы с промптами из БД
└── llm_logger.py         # Сервис для логирования вызовов в llm_calls

backend/alembic/versions/
└── 002_add_default_prompts.py  # Миграция с начальными промптами
```

## Компоненты

### 1. GigaChatClient (`app/llm/client.py`)

**Авторизация:**
- OAuth-запрос к `https://ngw.devices.sberbank.ru:9443/api/v2/oauth`
- Токен хранится в памяти с `expires_at`
- Обновление через `asyncio.Lock` (single-flight)
- Обновление за 120 секунд до истечения

**Слой A — `chat()`:**
- Отправляет запрос к GigaChat Chat API
- Обрабатывает HTTP-ошибки:
  - 401: refresh токена + retry (один раз)
  - 429: retry с backoff (учитывает Retry-After)
  - 402: `LlmQuotaExceeded` (без retry)
  - 400: `LlmUnavailable` (без retry)
  - 5xx: `LlmUnavailable` (после retry)
- Проверяет `finish_reason`:
  - `blacklist`: `LlmRefused`
  - `length`: контентная ошибка (retry в слое B)
- Параллелизм через `asyncio.Semaphore`

**Слой B — `chat_json()`:**
- Вызывает слой A
- Извлекает JSON из ответа (убирает markdown-блоки)
- Парсит JSON через `json.loads`
- Валидирует через Pydantic-схему
- При ошибке парсинга/валидации — retry (до `max_retries`)
- Возвращает валидированный Pydantic-объект

### 2. Исключения (`app/llm/exceptions.py`)

- `LlmError` — базовое исключение
- `LlmUnavailable` — сервис недоступен
- `LlmQuotaExceeded` — квота исчерпана
- `LlmInvalidResponse` — невалидный ответ
- `LlmRefused` — контент отклонён

### 3. PromptService (`app/services/prompt_service.py`)

- Читает промпты из таблицы `prompts`
- Если промпт не найден — использует fallback из кода
- Логирует критическую ошибку при отсутствии промпта
- Метод `format_prompt()` для подстановки плейсхолдеров

**Fallback-промпты:**
- `generate_sentences` — генерация предложений с плейсхолдерами `{level}`, `{count}`, `{word}`
- `evaluate_translation` — оценка перевода

### 4. LlmLogger (`app/services/llm_logger.py`)

- Логирует каждый вызов в таблицу `llm_calls`
- Автокоммит-транзакция (не блокирует основную операцию)
- Записывает: purpose, user_id, request, response, status, latency, tokens

### 5. Pydantic-схемы (`app/llm/schemas.py`)

- `GenerateSentencesResponse` — ответ генерации предложений
- `EvaluateTranslationResponse` — ответ оценки перевода
- `SentencePair` — пара (english, russian)
- `WordEvaluation` — оценка слова (word, status, feedback)

### 6. Миграция (`002_add_default_prompts.py`)

- Заполняет таблицу `prompts` начальными шаблонами
- Down-миграция удаляет записи

## Применение миграции

```bash
cd backend
alembic upgrade head
```

## Тесты

### Unit-тесты с моками

```bash
# Тесты клиента (с моками HTTP)
pytest tests/test_llm_client.py -v

# Тесты сервиса промптов
pytest tests/test_prompt_service.py -v
```

**Тестируемые сценарии:**

1. **Управление токеном:**
   - Обновление при истечении
   - Обновление за 120 секунд до истечения
   - Не обновление при валидном токене
   - Конкурентное обновление (single-flight)

2. **Слой A (chat):**
   - Успешный запрос
   - 401 с retry после refresh
   - 401 дважды → `LlmUnavailable`
   - 402 → `LlmQuotaExceeded`
   - Timeout → `LlmUnavailable`

3. **Слой B (chat_json):**
   - Парсинг валидного JSON
   - Извлечение из markdown-блока
   - Retry при невалидном JSON
   - `LlmRefused` при blacklist
   - Retry при ошибке валидации

4. **Извлечение JSON:**
   - JSON-объект
   - JSON-массив
   - Markdown-блоки
   - Вложенный JSON
   - Отсутствие JSON

5. **PromptService:**
   - Получение из БД
   - Fallback при отсутствии
   - Ошибка при неизвестном ключе
   - Форматирование с плейсхолдерами

## Использование

### Пример вызова генерации предложений

```python
from app.llm import gigachat_client
from app.llm.schemas import GenerateSentencesResponse
from app.services.prompt_service import PromptService
from app.services.llm_logger import LlmLogger

async def generate_sentences(session, user_id, word, level, count=3):
    # 1. Получить промпт
    prompt_service = PromptService(session)
    template = await prompt_service.get_prompt("generate_sentences")
    system_prompt = prompt_service.format_prompt(
        template,
        level=level,
        count=count,
        word=word
    )
    
    # 2. Подготовить сообщения
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Generate {count} sentences with '{word}'"}
    ]
    
    # 3. Вызвать LLM
    start_time = time.time()
    try:
        result = await gigachat_client.chat_json(
            messages=messages,
            validator=GenerateSentencesResponse,
            temperature=0.7,
            max_tokens=500,
            timeout=25.0,
            max_retries=2
        )
        
        # 4. Залогировать успех
        latency_ms = int((time.time() - start_time) * 1000)
        logger = LlmLogger(session)
        await logger.log_call(
            purpose="generate",
            user_id=user_id,
            request_data={"messages": messages},
            response_data=result.model_dump(),
            status="ok",
            latency_ms=latency_ms
        )
        
        return result
    
    except LlmError as e:
        # 5. Залогировать ошибку
        latency_ms = int((time.time() - start_time) * 1000)
        logger = LlmLogger(session)
        await logger.log_call(
            purpose="generate",
            user_id=user_id,
            request_data={"messages": messages},
            response_data=None,
            status="http_error",
            latency_ms=latency_ms
        )
        
        # 6. Создать событие llm_error
        await record_event(
            session,
            user_id,
            "llm_error",
            {"error_type": type(e).__name__, "message": str(e)}
        )
        
        raise
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

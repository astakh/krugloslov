# ✅ Добавлено логирование для диагностики GigaChat API

## Что было сделано

### 1. Исправлена критическая ошибка в логике таймаута

**Файл:** `backend/app/services/lesson_start_service.py`

**Проблема:**
```python
# БЫЛО (неправильно):
if time.time() - timeout > 0:
    raise LlmUnavailable("Timeout exceeded")
```

`time.time()` возвращает текущее время в секундах с начала эпохи (очень большое число), а `timeout` - это просто число секунд. Поэтому условие всегда было истинным, и таймаут срабатывал мгновенно!

**Решение:**
```python
# СТАЛО (правильно):
start_time = time.time()
# ...
elapsed = time.time() - start_time
if elapsed > timeout:
    raise LlmUnavailable(f"Timeout exceeded: {elapsed:.2f}s > {timeout}s")
```

Теперь правильно отслеживается время начала и сравнивается прошедшее время с таймаутом.

### 2. Добавлено подробное логирование

#### LLM Client (`backend/app/llm/client.py`)

**Получение токена:**
- URL запроса
- Заголовки (с маскированием ключа)
- Статус ответа
- Ключи данных в ответе

**Отправка запроса к модели:**
- URL API
- Параметры запроса (модель, температура, max_tokens, timeout)
- Количество сообщений
- Payload запроса (первые 500 символов)
- Статус ответа и время выполнения
- Ошибки API с телом ответа

#### Lesson Start Service (`backend/app/services/lesson_start_service.py`)

**Генерация предложений:**
- Количество групп и таймаут
- Информация о словах
- Шаблон промпта
- Длина системного и пользовательского промпта
- Номер попытки и прошедшее время
- Успешность получения ответа
- Результаты валидации
- Общее время генерации

### 3. Созданы диагностические инструменты

#### Тестовый скрипт: `backend/test_gigachat.py`

Проверяет:
1. ✅ Конфигурацию (ключи, таймауты, модель)
2. ✅ Получение токена
3. ✅ Простой запрос к модели
4. ✅ Генерацию предложений для урока

**Запуск:**
```bash
cd backend
python test_gigachat.py
```

#### Руководство по отладке: `backend/GIGACHAT_DEBUG_GUIDE.md`

Содержит:
- Описание всех добавленных логов
- Анализ типичных проблем
- Решения для каждой проблемы
- Полезные команды curl
- Ссылки на документацию

## Как использовать

### 1. Запустите тестовый скрипт

```bash
cd backend
python test_gigachat.py
```

Вы увидите:
```
============================================================
ТЕСТИРОВАНИЕ GIGACHAT API
============================================================

============================================================
1. Проверка конфигурации
============================================================
  AUTH_KEY: ********************abcd1234
  SCOPE: GIGACHAT_API_PERS
  MODEL: GigaChat
  ...
  ✅ Конфигурация проверена

============================================================
2. Получение токена
============================================================
  ✅ Токен получен: eyJhbGciOiJSUzI1NiIs...
  ✅ Длина токена: 512 символов

============================================================
3. Простой запрос к модели
============================================================
  Отправка запроса...
  ✅ Ответ получен: тест
  ✅ Finish reason: stop
  ✅ Tokens used: {'prompt_tokens': 10, 'completion_tokens': 5, ...}

============================================================
4. Тест генерации предложений для урока
============================================================
  Отправка запроса на генерацию...
  ✅ Ответ получен (250 символов)
  ✅ JSON распарсен успешно
  ✅ Найдено предложений: 2
     1. The cat runs fast.
        → Кот бегает быстро.
     2. He runs fast every morning.
        → Он бегает быстро каждое утро.

============================================================
РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ
============================================================
  Конфигурация: ✅ УСПЕХ
  Получение токена: ✅ УСПЕХ
  Простой запрос: ✅ УСПЕХ
  Генерация урока: ✅ УСПЕХ

🎉 Все тесты пройдены успешно!
   GigaChat API работает корректно.
============================================================
```

### 2. Включите DEBUG логирование

**Вариант A: Через переменную окружения**

Добавьте в `backend/.env`:
```env
LOG_LEVEL=DEBUG
```

**Вариант B: Через код**

Измените в `backend/app/main.py`:
```python
logging.basicConfig(
    level=logging.DEBUG,  # Было INFO
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 3. Перезапустите backend

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Попробуйте начать урок

В логах вы увидите подробную информацию:

```
INFO - Starting sentence generation for 2 groups, timeout=45.0s
DEBUG - Retrieved word info for 4 words
DEBUG - Loaded prompt template: You are an English language teacher...
INFO - Prepared messages for LLM: system=500 chars, user=300 chars
DEBUG - Attempt 1/3, elapsed=0.50s, timeout=45.0s
INFO - Calling GigaChat API (attempt 1)
INFO - Refreshing GigaChat token from https://ngw.devices.sberbank.ru:9443/api/v2/oauth
DEBUG - OAuth request headers: Authorization=Basic ***1234567890, RqUID=abc-123, scope=GIGACHAT_API_PERS
INFO - OAuth response status: 200
DEBUG - OAuth response data keys: ['access_token', 'expires_at']
INFO - Sending chat request to https://api.giga.chat/v1/chat/completions
DEBUG - Request params: model=GigaChat, temperature=0.7, max_tokens=2000, timeout=60s
DEBUG - Messages count: 2
DEBUG - Request payload: {"model": "GigaChat", "messages": [...]}...
INFO - Chat response status: 200 (elapsed: 5.23s)
INFO - LLM response received successfully
DEBUG - Validating 2 groups from LLM response
INFO - Validation result: 2 valid, 0 invalid
INFO - Sentence generation completed successfully in 6.50s, generated 2 groups
```

## Диагностика проблем

### Проблема 1: Ошибка получения токена

**В логах:**
```
ERROR - Failed to get GigaChat token: 401
ERROR - Response body: {"error": "invalid_client"}
```

**Решение:**
1. Проверьте `GIGACHAT_AUTH_KEY` в `.env`
2. Убедитесь, что ключ в формате Base64
3. Получите новый ключ в личном кабинете GigaChat

### Проблема 2: Таймаут запроса

**В логах:**
```
DEBUG - Attempt 1/3, elapsed=0.50s, timeout=45.0s
ERROR - Timeout exceeded: 45.50s > 45.0s
```

**Решение:**
1. Увеличьте `LLM_REQUEST_TIMEOUT` в `.env`:
   ```env
   LLM_REQUEST_TIMEOUT=120
   ```
2. Проверьте скорость интернет-соединения

### Проблема 3: Ошибка API

**В логах:**
```
INFO - Chat response status: 429 (elapsed: 1.23s)
ERROR - Chat API error: 429
ERROR - Response body: {"error": "rate_limit_exceeded"}
```

**Решение:**
1. Уменьшите `GIGACHAT_MAX_CONCURRENCY` в `.env`:
   ```env
   GIGACHAT_MAX_CONCURRENCY=1
   ```
2. Подождите перед повторной попыткой

### Проблема 4: Невалидный JSON

**В логах:**
```
WARNING - LLM returned invalid response: Invalid JSON format
INFO - Retrying after invalid response...
```

**Решение:**
1. Проверьте промпт в таблице `prompts`
2. Уменьшите `GEN_TEMPERATURE`:
   ```env
   GEN_TEMPERATURE=0.3
   ```

## Полезные команды

### Проверить доступность API

```bash
# Проверить OAuth endpoint
curl -I https://ngw.devices.sberbank.ru:9443/api/v2/oauth

# Проверить Chat endpoint
curl -I https://api.giga.chat/v1/chat/completions
```

### Получить токен вручную

```bash
curl -X POST "https://ngw.devices.sberbank.ru:9443/api/v2/oauth" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Accept: application/json" \
  -H "Authorization: Basic YOUR_AUTH_KEY" \
  -d "scope=GIGACHAT_API_PERS"
```

### Отправить тестовый запрос

```bash
curl -X POST "https://api.giga.chat/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "model": "GigaChat",
    "messages": [
      {"role": "user", "content": "Привет!"}
    ],
    "temperature": 0.7,
    "max_tokens": 100,
    "stream": false
  }'
```

## Измененные файлы

1. ✅ `backend/app/llm/client.py` - добавлено логирование
2. ✅ `backend/app/services/lesson_start_service.py` - исправлен таймаут, добавлено логирование
3. ✅ `backend/test_gigachat.py` - тестовый скрипт
4. ✅ `backend/GIGACHAT_DEBUG_GUIDE.md` - руководство по отладке

## Следующие шаги

1. Запустите `python test_gigachat.py` для быстрой диагностики
2. Включите DEBUG логирование
3. Перезапустите backend
4. Попробуйте начать урок
5. Изучите логи для диагностики проблем

## Документация

- `backend/GIGACHAT_DEBUG_GUIDE.md` - полное руководство по отладке
- [GigaChat API Documentation](https://developers.sber.ru/docs/ru/gigachat/api/main)

# Исправление проблемы с таймаутом GigaChat API

## Проблема

При попытке начать урок возникала ошибка:
```
ERROR app.services.lesson_start_service: LLM error during lesson generation: Timeout exceeded
POST /lesson/start - 503 Service Unavailable
```

## Причины

1. **Устаревший URL API**: В коде использовался старый URL `https://gigachat.devices.sberbank.ru/api/v1/chat/completions`, но согласно официальной документации правильный URL: `https://api.giga.chat/v1/chat/completions`

2. **Недостаточные таймауты**: Таймауты были слишком короткими для генерации предложений с LLM

3. **Отсутствие настроек таймаутов**: Не было возможности настроить таймауты через переменные окружения

## Решение

### 1. Обновлен URL API

**Файл:** `backend/app/llm/client.py`

```python
# Было:
CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

# Стало:
CHAT_URL = "https://api.giga.chat/v1/chat/completions"
```

### 2. Добавлены настройки таймаутов

**Файл:** `backend/app/config.py`

```python
# LLM timeouts
LLM_REQUEST_TIMEOUT: int = Field(default=60, ge=10, le=300, description="Request timeout in seconds")
LLM_TOKEN_TIMEOUT: int = Field(default=30, ge=10, le=120, description="Token refresh timeout in seconds")
```

### 3. Обновлен клиент GigaChat

**Файл:** `backend/app/llm/client.py`

- Метод `_refresh_token()` теперь использует `LLM_TOKEN_TIMEOUT`
- Метод `chat()` теперь использует `LLM_REQUEST_TIMEOUT`
- Добавлены заголовки `Accept: application/json` для соответствия API
- Добавлен параметр `stream: False` для явного указания непотокового режима

### 4. Обновлен .env.example

**Файл:** `backend/.env.example`

```env
# LLM timeouts (in seconds)
LLM_REQUEST_TIMEOUT=60
LLM_TOKEN_TIMEOUT=30
```

## Что нужно сделать

### 1. Обновите .env файл

Добавьте в `backend/.env`:

```env
# LLM timeouts (in seconds)
LLM_REQUEST_TIMEOUT=60
LLM_TOKEN_TIMEOUT=30
```

### 2. Перезапустите backend

```bash
# Остановите текущий процесс (Ctrl+C)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Проверьте работу

1. Откройте http://localhost:3000
2. Войдите в систему
3. Попробуйте начать урок
4. Ожидайте: урок должен создаться без ошибок таймаута

## Проверка подключения к GigaChat

### Тест через curl

```bash
# 1. Получите токен
curl -X POST "https://ngw.devices.sberbank.ru:9443/api/v2/oauth" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Accept: application/json" \
  -H "RqUID: $(uuidgen)" \
  -H "Authorization: Basic YOUR_AUTH_KEY" \
  -d "scope=GIGACHAT_API_PERS"

# Сохраните access_token из ответа

# 2. Проверьте список моделей
curl -X GET "https://api.giga.chat/v1/models" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# 3. Отправьте тестовый запрос
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

### Проверка через логи

В логах backend должны быть сообщения:
```
INFO: Loaded SSL certificate from ...
INFO: GigaChat token refreshed successfully
```

## Возможные проблемы

### Проблема 1: SSL ошибки

**Симптом:** `SSLCertVerificationError` или `CERTIFICATE_VERIFY_FAILED`

**Решение:**
1. Скачайте корневой сертификат НУЦ Минцифры
2. Укажите путь в `.env`:
   ```env
   GIGACHAT_CA_CERT_PATH=/path/to/cert.cer
   ```

### Проблема 2: Ошибка 401 Unauthorized

**Симптом:** `Failed to authenticate with GigaChat`

**Решение:**
1. Проверьте `GIGACHAT_AUTH_KEY` в `.env`
2. Убедитесь, что ключ в формате Base64
3. Проверьте `GIGACHAT_SCOPE` (должен быть `GIGACHAT_API_PERS` для физлиц)

### Проблема 3: Ошибка 429 Too Many Requests

**Симптом:** `Rate limit exceeded`

**Решение:**
1. Уменьшите `GIGACHAT_MAX_CONCURRENCY` в `.env`
2. Подождите перед повторной попыткой
3. Проверьте лимиты в личном кабинете GigaChat

### Проблема 4: Таймаут все еще возникает

**Решение:**
1. Увеличьте `LLM_REQUEST_TIMEOUT` в `.env`:
   ```env
   LLM_REQUEST_TIMEOUT=120
   ```
2. Проверьте скорость интернет-соединения
3. Проверьте доступность API через curl

## Настройки таймаутов

### LLM_REQUEST_TIMEOUT
- **Описание:** Таймаут для запросов к API генерации
- **По умолчанию:** 60 секунд
- **Минимум:** 10 секунд
- **Максимум:** 300 секунд (5 минут)
- **Рекомендация:** 60-120 секунд для генерации предложений

### LLM_TOKEN_TIMEOUT
- **Описание:** Таймаут для получения OAuth токена
- **По умолчанию:** 30 секунд
- **Минимум:** 10 секунд
- **Максимум:** 120 секунд
- **Рекомендация:** 30 секунд достаточно

## Архитектура клиента GigaChat

```
┌─────────────────────────────────────────────────────────┐
│                    GigaChatClient                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐                                       │
│  │ Token Info   │  ← Хранит access_token и expires_at  │
│  └──────────────┘                                       │
│                                                          │
│  ┌──────────────┐                                       │
│  │ Token Lock   │  ← Предотвращает параллельное        │
│  │ (asyncio)    │    обновление токена                  │
│  └──────────────┘                                       │
│                                                          │
│  ┌──────────────┐                                       │
│  │ Semaphore    │  ← Ограничивает параллельные         │
│  │              │    запросы к API                      │
│  └──────────────┘                                       │
│                                                          │
│  ┌──────────────┐                                       │
│  │ SSL Context  │  ← Опциональный сертификат           │
│  └──────────────┘                                       │
│                                                          │
└─────────────────────────────────────────────────────────┘
                          ↓
                    HTTP Requests
                          ↓
┌─────────────────────────────────────────────────────────┐
│                    GigaChat API                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  OAuth: https://ngw.devices.sberbank.ru:9443/api/v2/oauth│
│  Chat:  https://api.giga.chat/v1/chat/completions       │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Поток работы

### Получение токена
```
1. Проверить, есть ли токен
   ↓
2. Проверить, не истек ли токен (за 120 секунд до истечения)
   ↓
3. Если токен нужен:
   - Заблокировать token_lock
   - Отправить POST /oauth
   - Сохранить access_token и expires_at
   - Разблокировать token_lock
   ↓
4. Вернуть access_token
```

### Отправка запроса к модели
```
1. Получить токен (см. выше)
   ↓
2. Захватить semaphore (ограничение параллелизма)
   ↓
3. Отправить POST /chat/completions
   ↓
4. Обработать ответ:
   - 200: вернуть результат
   - 401: обновить токен и повторить один раз
   - 429: повторить с backoff
   - 402: LlmQuotaExceeded
   - 5xx: LlmUnavailable
   ↓
5. Освободить semaphore
```

## Документация GigaChat API

- **Официальная документация:** https://developers.sber.ru/docs/ru/gigachat/api/main
- **Получение токена:** https://developers.sber.ru/docs/ru/gigachat/api/reference/rest/post-token
- **Генерация ответа:** https://developers.sber.ru/docs/ru/gigachat/api/reference/rest/post-chat
- **Ошибки:** https://developers.sber.ru/docs/ru/gigachat/api/errors-description
- **Тарифы:** https://developers.sber.ru/docs/ru/gigachat/api/tariffs

## Статус

✅ URL API обновлен  
✅ Таймауты увеличены  
✅ Настройки вынесены в конфигурацию  
✅ Добавлены заголовки Accept  
✅ Добавлен параметр stream: false  
✅ .env.example обновлен  
✅ Документация создана  
✅ Готово к использованию  

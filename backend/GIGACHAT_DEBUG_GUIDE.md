# Диагностика проблем с GigaChat API

## Добавленное логирование

В код добавлено подробное логирование для диагностики проблем:

### 1. LLM Client (`backend/app/llm/client.py`)

#### Получение токена
```python
logger.info(f"Refreshing GigaChat token from {self.OAUTH_URL}")
logger.debug(f"OAuth request headers: Authorization=Basic ***{settings.GIGACHAT_AUTH_KEY[-10:]}, RqUID={headers['RqUID']}, scope={settings.GIGACHAT_SCOPE}")
logger.info(f"OAuth response status: {response.status_code}")
logger.debug(f"OAuth response data keys: {list(data.keys())}")
```

#### Отправка запроса к модели
```python
logger.info(f"Sending chat request to {self.CHAT_URL}")
logger.debug(f"Request params: model={settings.GIGACHAT_MODEL}, temperature={temperature}, max_tokens={max_tokens}, timeout={effective_timeout}s")
logger.debug(f"Messages count: {len(messages)}")
logger.debug(f"Request payload: {json.dumps(request_data, ensure_ascii=False)[:500]}...")
logger.info(f"Chat response status: {response.status_code} (elapsed: {elapsed:.2f}s)")
```

### 2. Lesson Start Service (`backend/app/services/lesson_start_service.py`)

#### Генерация предложений
```python
logger.info(f"Starting sentence generation for {len(groups)} groups, timeout={timeout}s")
logger.debug(f"Retrieved word info for {len(word_ids)} words")
logger.debug(f"Loaded prompt template: {template[:100]}...")
logger.info(f"Prepared messages for LLM: system={len(system_prompt)} chars, user={len(user_prompt)} chars")
logger.debug(f"Attempt {attempt + 1}/{max_retries + 1}, elapsed={elapsed:.2f}s, timeout={timeout}s")
logger.info(f"Calling GigaChat API (attempt {attempt + 1})")
logger.info(f"LLM response received successfully")
logger.debug(f"Validating {len(response.groups)} groups from LLM response")
logger.info(f"Validation result: {len(valid_indices)} valid, {len(new_invalid_indices)} invalid")
logger.info(f"Sentence generation completed successfully in {total_elapsed:.2f}s, generated {len(valid_groups)} groups")
```

## Как использовать логи

### 1. Установите уровень логирования DEBUG

В `backend/.env` добавьте:
```env
LOG_LEVEL=DEBUG
```

Или измените в коде `backend/app/main.py`:
```python
logging.basicConfig(
    level=logging.DEBUG,  # Было INFO
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 2. Перезапустите backend

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Попробуйте начать урок

В логах вы увидите подробную информацию о каждом этапе.

## Анализ логов

### Успешный сценарий

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

### Проблемы и их диагностика

#### 1. Ошибка получения токена

**Симптом:**
```
INFO - Refreshing GigaChat token from https://ngw.devices.sberbank.ru:9443/api/v2/oauth
ERROR - Failed to get GigaChat token: 401
ERROR - Response body: {"error": "invalid_client"}
```

**Причины:**
- Неправильный `GIGACHAT_AUTH_KEY` в `.env`
- Неправильный `GIGACHAT_SCOPE`
- Истек срок действия ключа авторизации

**Решение:**
1. Проверьте `GIGACHAT_AUTH_KEY` в `.env`
2. Убедитесь, что ключ в формате Base64
3. Проверьте `GIGACHAT_SCOPE` (должен быть `GIGACHAT_API_PERS` для физлиц)
4. Получите новый ключ в личном кабинете GigaChat

#### 2. Таймаут запроса

**Симптом:**
```
DEBUG - Attempt 1/3, elapsed=0.50s, timeout=45.0s
INFO - Calling GigaChat API (attempt 1)
INFO - Sending chat request to https://api.giga.chat/v1/chat/completions
ERROR - Timeout exceeded: 45.50s > 45.0s
```

**Причины:**
- Медленное интернет-соединение
- GigaChat API перегружен
- Слишком короткий таймаут

**Решение:**
1. Увеличьте `LLM_REQUEST_TIMEOUT` в `.env`:
   ```env
   LLM_REQUEST_TIMEOUT=120
   ```
2. Проверьте скорость интернет-соединения
3. Попробуйте позже (возможно, API перегружен)

#### 3. Ошибка API

**Симптом:**
```
INFO - Sending chat request to https://api.giga.chat/v1/chat/completions
INFO - Chat response status: 429 (elapsed: 1.23s)
ERROR - Chat API error: 429
ERROR - Response body: {"error": "rate_limit_exceeded"}
```

**Причины:**
- Превышен лимит запросов
- Недостаточно токенов на аккаунте

**Решение:**
1. Уменьшите `GIGACHAT_MAX_CONCURRENCY` в `.env`:
   ```env
   GIGACHAT_MAX_CONCURRENCY=1
   ```
2. Подождите перед повторной попыткой
3. Проверьте баланс токенов в личном кабинете GigaChat

#### 4. Невалидный ответ от LLM

**Симптом:**
```
INFO - LLM response received successfully
DEBUG - Validating 2 groups from LLM response
WARNING - LLM returned invalid response: Invalid JSON format
INFO - Retrying after invalid response...
```

**Причины:**
- LLM вернул невалидный JSON
- Ответ не соответствует ожидаемой схеме

**Решение:**
1. Проверьте промпт в таблице `prompts`
2. Убедитесь, что промпт четко требует JSON формат
3. Попробуйте изменить `GEN_TEMPERATURE` (меньше = стабильнее):
   ```env
   GEN_TEMPERATURE=0.3
   ```

## Тестовый скрипт

Создайте файл `backend/test_gigachat.py`:

```python
"""Test script for GigaChat API connection."""

import asyncio
import logging
from app.llm import gigachat_client
from app.llm.schemas import GenerateSentencesResponse

logging.basicConfig(level=logging.DEBUG)

async def test_gigachat():
    """Test GigaChat API connection."""
    print("Testing GigaChat API connection...")
    
    # Test 1: Get token
    print("\n1. Getting token...")
    try:
        token = await gigachat_client._get_token()
        print(f"✅ Token obtained: {token[:20]}...")
    except Exception as e:
        print(f"❌ Failed to get token: {e}")
        return
    
    # Test 2: Simple chat
    print("\n2. Sending simple chat request...")
    try:
        messages = [
            {"role": "user", "content": "Привет! Скажи 'тест'."}
        ]
        
        response = await gigachat_client.chat(
            messages=messages,
            temperature=0.7,
            max_tokens=50,
            timeout=30.0,
        )
        
        print(f"✅ Response received: {response['content'][:100]}...")
    except Exception as e:
        print(f"❌ Chat request failed: {e}")
        return
    
    # Test 3: JSON response
    print("\n3. Testing JSON response...")
    try:
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Always respond with valid JSON."},
            {"role": "user", "content": 'Return JSON: {"test": "value"}'}
        ]
        
        response = await gigachat_client.chat_json(
            messages=messages,
            validator=GenerateSentencesResponse,
            temperature=0.1,
            max_tokens=500,
            timeout=30.0,
            max_retries=1,
        )
        
        print(f"✅ JSON response validated successfully")
    except Exception as e:
        print(f"❌ JSON validation failed: {e}")
        print(f"   This is expected if response doesn't match schema")
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    asyncio.run(test_gigachat())
```

Запуск:
```bash
cd backend
python test_gigachat.py
```

## Проверка конфигурации

Создайте файл `backend/check_config.py`:

```python
"""Check GigaChat configuration."""

from app.config import settings

print("GigaChat Configuration:")
print(f"  AUTH_KEY: {'*' * 20}{settings.GIGACHAT_AUTH_KEY[-10:]}")
print(f"  SCOPE: {settings.GIGACHAT_SCOPE}")
print(f"  MODEL: {settings.GIGACHAT_MODEL}")
print(f"  CA_CERT_PATH: {settings.GIGACHAT_CA_CERT_PATH or '(not set)'}")
print(f"  MAX_CONCURRENCY: {settings.GIGACHAT_MAX_CONCURRENCY}")
print(f"  REQUEST_TIMEOUT: {settings.LLM_REQUEST_TIMEOUT}s")
print(f"  TOKEN_TIMEOUT: {settings.LLM_TOKEN_TIMEOUT}s")
print(f"  GEN_TEMPERATURE: {settings.GEN_TEMPERATURE}")
print(f"  EVAL_TEMPERATURE: {settings.EVAL_TEMPERATURE}")
```

Запуск:
```bash
cd backend
python check_config.py
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

## Документация

- [GigaChat API Documentation](https://developers.sber.ru/docs/ru/gigachat/api/main)
- [OAuth Token](https://developers.sber.ru/docs/ru/gigachat/api/reference/rest/post-token)
- [Chat Completions](https://developers.sber.ru/docs/ru/gigachat/api/reference/rest/post-chat)
- [Errors](https://developers.sber.ru/docs/ru/gigachat/api/errors-description)

# ✅ Исправлена проблема с таймаутом GigaChat API

## Что было исправлено

**Проблема:** При попытке начать урок возникала ошибка `Timeout exceeded`

**Причины:**
1. Устаревший URL API (`gigachat.devices.sberbank.ru` вместо `api.giga.chat`)
2. Недостаточные таймауты для генерации предложений
3. Отсутствие настроек таймаутов в конфигурации

## Изменения

### 1. Обновлен URL API
**Файл:** `backend/app/llm/client.py`
```python
CHAT_URL = "https://api.giga.chat/v1/chat/completions"
```

### 2. Добавлены настройки таймаутов
**Файл:** `backend/app/config.py`
```python
LLM_REQUEST_TIMEOUT: int = 60  # секунд
LLM_TOKEN_TIMEOUT: int = 30    # секунд
```

### 3. Обновлен клиент GigaChat
- Увеличены таймауты
- Добавлены заголовки `Accept: application/json`
- Добавлен параметр `stream: false`

### 4. Обновлен .env.example
Добавлены новые переменные окружения

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
4. **Ожидайте:** урок должен создаться без ошибок таймаута

## Проверка подключения к GigaChat

### Быстрый тест через curl

```bash
# 1. Получите токен (замените YOUR_AUTH_KEY на ваш ключ)
curl -X POST "https://ngw.devices.sberbank.ru:9443/api/v2/oauth" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Accept: application/json" \
  -H "Authorization: Basic YOUR_AUTH_KEY" \
  -d "scope=GIGACHAT_API_PERS"

# Сохраните access_token из ответа

# 2. Проверьте список моделей
curl -X GET "https://api.giga.chat/v1/models" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Возможные проблемы

### SSL ошибки
**Решение:** Скачайте корневой сертификат НУЦ Минцифры и укажите путь в `.env`:
```env
GIGACHAT_CA_CERT_PATH=/path/to/cert.cer
```

### Ошибка 401 Unauthorized
**Решение:** Проверьте `GIGACHAT_AUTH_KEY` в `.env`

### Таймаут все еще возникает
**Решение:** Увеличьте `LLM_REQUEST_TIMEOUT` в `.env`:
```env
LLM_REQUEST_TIMEOUT=120
```

## Документация

Полная документация: `backend/FIX_GIGACHAT_TIMEOUT.md`

## Статус

✅ URL API обновлен  
✅ Таймауты увеличены  
✅ Настройки вынесены в конфигурацию  
✅ Готово к использованию  

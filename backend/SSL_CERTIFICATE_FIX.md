# 🔐 Решение проблемы с SSL сертификатом GigaChat API

## Проблема

```
[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self signed certificate in certificate chain
```

Серверы GigaChat используют корневой сертификат НУЦ Минцифры (Министерство цифрового развития РФ), которого нет в стандартных хранилищах Windows.

## Быстрое решение (для разработки)

Сейчас код автоматически отключает проверку SSL, если не указан путь к сертификату. Это позволит работать с API сразу.

**Временно отключена проверка SSL** - вы можете начать работу немедленно!

## Правильное решение (для продакшена)

### Вариант 1: Автоматическая загрузка сертификата

```bash
cd backend
python scripts/download_gigachat_cert.py
```

Скрипт:
- ✅ Скачает корневой сертификат НУЦ Минцифры
- ✅ Сохранит в `backend/certs/russian_trusted_root_ca.cer`
- ✅ Покажет инструкции по настройке

После выполнения скрипта:

1. Добавьте в `backend/.env`:
   ```env
   GIGACHAT_CA_CERT_PATH=D:/krugoslov/backend/certs/russian_trusted_root_ca.cer
   ```

2. Перезапустите backend:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. Проверьте работу:
   ```bash
   python test_gigachat.py
   ```

### Вариант 2: Ручная загрузка сертификата

1. Скачайте сертификат:
   - https://gu-st.ru/content/lending/russian_trusted_root_ca.cer

2. Сохраните в `backend/certs/russian_trusted_root_ca.cer`

3. Добавьте в `backend/.env`:
   ```env
   GIGACHAT_CA_CERT_PATH=D:/krugoslov/backend/certs/russian_trusted_root_ca.cer
   ```

4. Перезапустите backend

### Вариант 3: Установка в системное хранилище Windows

1. Скачайте сертификат (см. Вариант 2)

2. Установите в систему:
   - Откройте скачанный файл `.cer`
   - Нажмите "Установить сертификат"
   - Выберите "Локальная машина"
   - Выберите "Поместить все сертификаты в следующее хранилище"
   - Выберите "Доверенные корневые центры сертификации"
   - Завершите установку

3. Перезапустите backend (без указания `GIGACHAT_CA_CERT_PATH`)

## Проверка работы

### Тест 1: Скрипт проверки

```bash
cd backend
python test_gigachat.py
```

Ожидаемый результат:
```
✅ Токен получен
✅ Простой запрос выполнен
✅ Генерация предложений работает
```

### Тест 2: Начало урока

1. Откройте http://localhost:3000
2. Войдите в систему
3. Попробуйте начать урок
4. В логах backend должно быть:
   ```
   INFO - Refreshing GigaChat token from https://ngw.devices.sberbank.ru:9443/api/v2/oauth
   INFO - OAuth response status: 200
   INFO - Sending chat request to https://api.giga.chat/v1/chat/completions
   INFO - Chat response status: 200 (elapsed: 5.23s)
   INFO - LLM response received successfully
   ```

## Настройки в .env

### Для разработки (без проверки SSL)

```env
# Удалите или закомментируйте строку
# GIGACHAT_CA_CERT_PATH=

# Или оставьте пустой
GIGACHAT_CA_CERT_PATH=
```

### Для продакшена (с проверкой SSL)

```env
# Укажите путь к сертификату
GIGACHAT_CA_CERT_PATH=D:/krugoslov/backend/certs/russian_trusted_root_ca.cer
```

## Логи при успешном подключении

```
INFO - Starting sentence generation for 2 groups, timeout=45.0s
DEBUG - Retrieved word info for 4 words
DEBUG - Loaded prompt template: You are an English language teacher...
INFO - Prepared messages for LLM: system=512 chars, user=182 chars
DEBUG - Attempt 1/3, elapsed=0.50s, timeout=45.0s
INFO - Calling GigaChat API (attempt 1)
INFO - Refreshing GigaChat token from https://ngw.devices.sberbank.ru:9443/api/v2/oauth
DEBUG - OAuth request headers: Authorization=Basic ***abcd1234, RqUID=abc-123, scope=GIGACHAT_API_PERS
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

## Логи при ошибке SSL (до исправления)

```
INFO - Refreshing GigaChat token from https://ngw.devices.sberbank.ru:9443/api/v2/oauth
ERROR - Network error during token refresh: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self signed certificate in certificate chain
ERROR - LLM error on attempt 1: LlmUnavailable: Failed to connect to GigaChat OAuth
```

## Альтернативные решения

### Если скрипт не может скачать сертификат

1. Откройте браузер
2. Перейдите по ссылке: https://gu-st.ru/content/lending/russian_trusted_root_ca.cer
3. Скачайте файл
4. Сохраните в `backend/certs/russian_trusted_root_ca.cer`

### Если сертификат не помогает

1. Проверьте, что файл сертификата существует:
   ```bash
   dir backend\certs\russian_trusted_root_ca.cer
   ```

2. Проверьте путь в `.env`:
   ```env
   GIGACHAT_CA_CERT_PATH=D:/krugoslov/backend/certs/russian_trusted_root_ca.cer
   ```

3. Используйте абсолютный путь с прямыми слешами (`/`)

### Если ничего не помогает

Временно отключите проверку SSL (только для разработки!):

```env
# Удалите или закомментируйте строку
# GIGACHAT_CA_CERT_PATH=
```

Код автоматически отключит проверку SSL.

## Безопасность

⚠️ **ВНИМАНИЕ:** Отключение проверки SSL делает соединение уязвимым для атак "человек посередине".

- ✅ **Для разработки:** Можно отключить проверку SSL
- ❌ **Для продакшена:** Обязательно используйте сертификат

## Документация

- [GigaChat SSL Troubleshooting](https://developers.sber.ru/docs/ru/gigachat/api/main)
- [НУЦ Минцифры](https://www.ministry.digital.gov.ru/)
- [Корневой сертификат](https://gu-st.ru/content/lending/russian_trusted_root_ca.cer)

## Структура файлов

```
backend/
├── certs/
│   └── russian_trusted_root_ca.cer  ← Корневой сертификат
├── scripts/
│   └── download_gigachat_cert.py    ← Скрипт для скачивания
└── .env                              ← Конфигурация
```

## Статус

✅ Код обновлен для автоматического отключения SSL при отсутствии сертификата  
✅ Создан скрипт для скачивания сертификата  
✅ Создана подробная документация  
✅ Готово к использованию  

## Следующие шаги

1. **Для быстрой проверки:** Просто перезапустите backend - SSL проверка будет отключена
2. **Для продакшена:** Запустите `python scripts/download_gigachat_cert.py` и настройте `.env`
3. **Для проверки:** Запустите `python test_gigachat.py`

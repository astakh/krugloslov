# Исправление ошибки SSL сертификата

## Проблема

При запуске backend возникала ошибка:
```
FileNotFoundError: [Errno 2] No such file or directory
```

Это происходило из-за того, что код пытался загрузить SSL сертификат для GigaChat, но файл не существовал или путь был пустым.

## Решение

Исправлен файл `backend/app/llm/client.py`:
- Добавлена проверка существования файла сертификата перед загрузкой
- Если файл не найден, используется стандартный SSL контекст
- Добавлены информативные сообщения в лог

## Проверка исправления

Запустите тестовый скрипт:

```bash
cd backend
python test_client_init.py
```

Ожидаемый вывод:
```
Testing configuration...
✓ Configuration loaded successfully
  DATABASE_URL: postgresql+asyncpg://...
  GIGACHAT_CA_CERT_PATH: ''
  GIGACHAT_MAX_CONCURRENCY: 3

Testing GigaChat client initialization...
✓ GigaChatClient initialized successfully
  SSL context: None
  Semaphore: <asyncio.locks.Semaphore object at 0x...>

✅ All tests passed! You can now run the server.
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Настройка .env

Убедитесь, что в файле `.env` переменная `GIGACHAT_CA_CERT_PATH` пустая:

```env
GIGACHAT_CA_CERT_PATH=
```

Или закомментируйте её:

```env
# GIGACHAT_CA_CERT_PATH=
```

## Запуск backend

После проверки запустите сервер:

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Сервер должен запуститься без ошибок SSL.

## Если проблема сохраняется

1. Проверьте, что файл `.env` существует в папке `backend/`
2. Убедитесь, что `GIGACHAT_CA_CERT_PATH` пустая или закомментирована
3. Проверьте логи - должны быть предупреждения о том, что сертификат не найден, но это нормально
4. Попробуйте очистить кэш Python:
   ```bash
   cd backend
   rmdir /s /q __pycache__
   rmdir /s /q app\__pycache__
   ```

## Дополнительная информация

См. файл `ENV_SETUP_WINDOWS.md` для подробной инструкции по настройке `.env`.

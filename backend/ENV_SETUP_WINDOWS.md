# Настройка .env файла для Windows

## Быстрая настройка

1. Скопируйте `.env.example` в `.env`:
```bash
copy .env.example .env
```

2. Отредактируйте `.env` и заполните обязательные поля:

### Обязательные параметры

```env
# Database - подключитесь к вашей удалённой БД PostgreSQL
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/krugloslov

# JWT - сгенерируйте случайную строку минимум 16 символов
JWT_SECRET=your-super-secret-key-change-this-in-production

# GigaChat - получите ключ на https://giga.chat
GIGACHAT_AUTH_KEY=your-gigachat-auth-key-here
```

### Необязательные параметры (можно оставить по умолчанию)

```env
# SSL сертификат для GigaChat (оставьте пустым, если не нужен)
GIGACHAT_CA_CERT_PATH=

# Остальные параметры имеют разумные значения по умолчанию
```

## Пример .env файла

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:mysecretpassword@db.example.com:5432/krugloslov

# JWT
JWT_SECRET=my-super-secret-jwt-key-12345678
ACCESS_TOKEN_TTL_MIN=15
REFRESH_TOKEN_TTL_DAYS=30

# Lesson settings
WORDS_PER_LESSON=10
DAILY_LESSON_LIMIT_DEFAULT=5
DAILY_LESSON_LIMIT_MAX=20

# GigaChat
GIGACHAT_AUTH_KEY=your-actual-gigachat-auth-key
GIGACHAT_SCOPE=GIGACHAT_API_PERS
GIGACHAT_MODEL=GigaChat
GIGACHAT_CA_CERT_PATH=
GIGACHAT_MAX_CONCURRENCY=3

# LLM temperatures
GEN_TEMPERATURE=0.7
EVAL_TEMPERATURE=0.1

# Logging
LLM_LOG_RETENTION_DAYS=30

# CORS
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

## Проверка подключения к БД

После настройки `.env`, проверьте подключение:

```bash
python -c "from app.config import settings; print('DB URL:', settings.DATABASE_URL[:50] + '...')"
```

## Запуск миграций

```bash
alembic upgrade head
```

## Запуск backend

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Решение проблем

### Ошибка: "No such file or directory" для SSL сертификата

Если вы видите ошибку:
```
FileNotFoundError: [Errno 2] No such file or directory: ''
```

**Решение:** Убедитесь, что в `.env` файле `GIGACHAT_CA_CERT_PATH=` пустое или закомментируйте эту строку.

### Ошибка подключения к БД

Проверьте:
1. Правильность `DATABASE_URL`
2. Доступность хоста БД
3. Правильность логина/пароля
4. Существование базы данных

### Ошибка с GigaChat

Получите актуальный ключ авторизации на https://giga.chat и обновите `GIGACHAT_AUTH_KEY` в `.env`.

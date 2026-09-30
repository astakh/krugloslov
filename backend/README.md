# Круглослов — Backend

FastAPI-приложение для интервального повторения английских слов.

## Структура

```
backend/
├── alembic/              # Миграции БД
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── app/
│   ├── main.py           # Фабрика приложения
│   ├── config.py         # Конфигурация (env vars)
│   ├── constants.py      # Константы (языки)
│   ├── database.py       # SQLAlchemy async engine
│   ├── exceptions.py     # Кастомные исключения
│   ├── middleware/       # Middleware (логирование)
│   ├── routers/          # API-роутеры
│   ├── schemas/          # Pydantic-схемы
│   ├── services/         # Бизнес-логика
│   ├── repositories/     # Доступ к БД
│   ├── security/         # JWT, хэши
│   └── llm/              # GigaChat клиент
├── tests/                # Тесты
├── requirements.txt
├── alembic.ini
└── .env.example
```

## Установка

```bash
cd backend
python -m venv venv
source venv/bin/activate  # или venv\Scripts\activate на Windows
pip install -r requirements.txt
```

## Конфигурация

Скопируйте `.env.example` в `.env` и заполните значения:

```bash
cp .env.example .env
```

Обязательные переменные:
- `DATABASE_URL` — строка подключения к PostgreSQL (asyncpg)
- `JWT_SECRET` — секрет для JWT (минимум 16 символов)
- `GIGACHAT_AUTH_KEY` — ключ авторизации GigaChat

## Запуск

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Проверка

### Health check
```bash
curl http://localhost:8000/health
# Ожидается: {"status":"ok"}
```

### Формат ошибок
```bash
curl http://localhost:8000/nonexistent
# Ожидается: 404 с телом {"error":{"code":"...","message":"...","details":{}}}
```

## Миграции

```bash
# Создать миграцию
alembic revision --autogenerate -m "description"

# Применить миграции
alembic upgrade head

# Откатить последнюю миграцию
alembic downgrade -1
```

## Тесты

```bash
pip install pytest pytest-asyncio httpx
pytest tests/ -v
```

## Константы

- `NATIVE_LANGUAGE = "ru"` — родной язык пользователя
- `TARGET_LANGUAGE = "en"` — изучаемый язык

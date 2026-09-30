# Круглослов — Backend

FastAPI-приложение для интервального повторения английских слов.

## Структура

```
backend/
├── alembic/                    # Миграции БД
│   ├── versions/
│   │   └── 001_initial_schema.py
│   ├── env.py
│   └── script.py.mako
├── app/
│   ├── main.py                 # Фабрика приложения (create_app)
│   ├── config.py               # Конфигурация через pydantic-settings
│   ├── constants.py            # NATIVE_LANGUAGE, TARGET_LANGUAGE
│   ├── database.py             # SQLAlchemy async engine + session
│   ├── exceptions.py           # Кастомные исключения (AppException и наследники)
│   ├── models/                 # SQLAlchemy ORM модели (17 таблиц)
│   │   ├── base.py             # Declarative Base
│   │   ├── user.py
│   │   ├── refresh_token.py
│   │   ├── dictionary.py
│   │   ├── word.py
│   │   ├── dictionary_word.py
│   │   ├── learning_profile.py
│   │   ├── user_word.py
│   │   ├── lesson.py
│   │   ├── lesson_exercise.py
│   │   ├── lesson_exercise_word.py
│   │   ├── lesson_exercise_suggestion.py
│   │   ├── sentence_report.py
│   │   ├── llm_call.py
│   │   ├── event.py
│   │   ├── dictionary_import.py
│   │   ├── prompt.py
│   │   └── prompt_history.py
│   ├── routers/                # API-роутеры
│   │   └── health.py           # GET /health
│   ├── schemas/                # Pydantic-схемы (ошибки и т.д.)
│   ├── services/               # Бизнес-логика
│   │   └── events.py           # Запись событий
│   ├── repositories/           # Доступ к БД
│   │   ├── user_repo.py
│   │   ├── word_repo.py
│   │   └── lesson_repo.py
│   ├── security/               # JWT, хэши (будет реализовано)
│   ├── llm/                    # GigaChat клиент (будет реализовано)
│   └── middleware/             # Middleware (логирование запросов)
├── tests/
│   ├── test_health.py          # Тесты health-эндпоинта
│   ├── test_models.py          # Unit-тесты моделей и нормализации
│   ├── test_constraints.py     # Интеграционные тесты ограничений БД
│   └── test_events_service.py  # Тесты сервиса событий
├── requirements.txt
├── alembic.ini
├── pytest.ini
└── .env.example
```

## Таблицы БД

| # | Таблица | Описание |
|---|---------|----------|
| 1 | users | Пользователи |
| 2 | refresh_tokens | JWT refresh-токены с ротацией |
| 3 | dictionaries | Словари слов |
| 4 | words | Английские слова с переводами |
| 5 | dictionary_words | Связь слов и словарей |
| 6 | learning_profiles | Профили обучения (1:1 с user) |
| 7 | user_words | Состояние изучения слов |
| 8 | lessons | Уроки |
| 9 | lesson_exercises | Упражнения в уроке |
| 10 | lesson_exercise_words | Слова в упражнении |
| 11 | lesson_exercise_suggestions | Подсказки LLM |
| 12 | sentence_reports | Жалобы на предложения |
| 13 | llm_calls | Лог вызовов LLM |
| 14 | events | Журнал событий |
| 15 | dictionary_imports | Логи импорта словарей |
| 16 | prompts | Текущие шаблоны промптов |
| 17 | prompt_history | История изменений промптов |

## Ключевые ограничения БД

- **users**: уникальный email (case-insensitive через функциональный индекс)
- **words**: уникальный (lemma_key, pos); CHECK на pos и level
- **dictionaries**: частичный уникальный индекс — только один is_general=true
- **user_words**: уникальный (profile_id, word_id); CHECK stage 0-6; due_lesson_number только для active
- **lessons**: уникальный (profile_id, lesson_number); частичный индекс — только один in_progress на профиль
- **sentence_reports**: уникальный (user_id, exercise_id)
- **lesson_exercise_suggestions**: уникальный (exercise_id, word_id)

## Установка

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Заполните DATABASE_URL и другие переменные
```

## Применение миграций

```bash
alembic upgrade head
```

## Запуск

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Тесты

### Unit-тесты (без БД)
```bash
pytest tests/test_models.py tests/test_events_service.py -v
```

### Интеграционные тесты (требуют PostgreSQL)
```bash
export TEST_DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/krugloslov_test"
pytest tests/test_constraints.py -v
```

## Нормализация леммы

```python
from app.repositories.word_repo import normalize_lemma
key = normalize_lemma("  Café  ")  # → "café"
```

Формула: `casefold(NFC(trim(lemma)))`

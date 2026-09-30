# Круглослов — Полная реализация MVP

## Обзор проекта

Веб-приложение для интервального повторения английских слов в контексте сгенерированных LLM предложений.

## Реализованные части

### Часть 0: Каркас проекта ✅
- Backend: FastAPI + SQLAlchemy + Alembic + PostgreSQL
- Frontend: React + Vite + TypeScript + Tailwind CSS
- Структура проекта, конфигурация, CORS, логирование
- Базовые модели и миграции (17 таблиц)

### Часть 1: Схема базы данных ✅
- 17 таблиц с полным набором ограничений
- CHECK constraints для enum-полей
- Уникальные индексы (email, lemma_key+pos, etc.)
- Частичные индексы (is_general, in_progress)
- Foreign keys с каскадным удалением

### Часть 2: Аутентификация ✅
- Регистрация и вход по email/пароль
- JWT access tokens + refresh tokens с ротацией
- HttpOnly cookies для refresh tokens
- Rate limiting (10 запросов/мин)
- Блокировка после 5 неудачных попыток
- Защита от replay-атак (отзыв family)

### Часть 3: Админка и импорт словарей ✅
- Защита админских эндпоинтов (is_admin)
- Импорт словарей из JSON
- Dry-run режим (валидация без записи)
- Advisory locks для предотвращения конфликтов
- Отчёты с ошибками (первые 200)
- Фикстура общего словаря

### Часть 4: Онбординг ✅
- Двухшаговый онбординг (часовой пояс + уровень)
- Валидация IANA timezones
- Создание learning_profile
- Привязка к общему словарю
- Событие onboarding_completed

### Часть 5: Главный экран и Dashboard ✅
- Эндпоинт GET /dashboard/summary
- Расчёт стрика (текущая серия, рекорд)
- Подсчёт уроков за сегодня
- Сводка слов (active, mastered, ignored)
- CTA логика (start, resume, limit_reached)
- Frontend: карточки стрика, уроков, слов

### Часть 6: Подбор слов для урока ✅
- Эндпоинт POST /lesson/preview
- Детерминированный подбор через SHA256 ранжирование
- Due-слова (повторение) + новые слова
- Ограничения по уровням
- Эндпоинт POST /lesson/new-word/decline
- Отказ от слова с пересчётом
- Состояния: resume, limit_reached, ready, no_words

## Архитектура

### Backend
```
backend/
├── app/
│   ├── main.py                 # FastAPI приложение
│   ├── config.py               # Конфигурация
│   ├── constants.py            # Константы (языки)
│   ├── database.py             # SQLAlchemy engine
│   ├── dependencies.py         # FastAPI зависимости
│   ├── exceptions.py           # Кастомные исключения
│   ├── models/                 # SQLAlchemy модели (17 таблиц)
│   ├── routers/                # API роутеры
│   │   ├── auth.py            # Аутентификация
│   │   ├── admin.py           # Админка
│   │   ├── onboarding.py      # Онбординг
│   │   ├── dashboard.py       # Dashboard
│   │   └── lesson.py          # Подбор слов
│   ├── schemas/                # Pydantic схемы
│   ├── services/               # Бизнес-логика
│   │   ├── auth.py            # AuthService
│   │   ├── onboarding.py      # OnboardingService
│   │   ├── dashboard_service.py
│   │   ├── lesson_preview_service.py
│   │   ├── streak_service.py  # Расчёт стрика
│   │   ├── dictionary_import.py
│   │   ├── prompt_service.py  # Работа с промптами
│   │   └── llm_logger.py      # Логирование LLM вызовов
│   ├── repositories/           # Доступ к БД
│   ├── security/               # JWT, password hashing, rate limiter
│   ├── llm/                    # LLM интеграция
│   │   ├── client.py          # GigaChat клиент
│   │   ├── exceptions.py      # LLM исключения
│   │   └── schemas.py         # Pydantic схемы для LLM
│   └── middleware/             # Логирование запросов
├── alembic/                    # Миграции
├── tests/                      # Тесты
└── fixtures/                   # Тестовые данные
```

### Frontend
```
src/
├── App.tsx                     # Главный компонент
├── main.tsx                    # Точка входа
├── index.css                   # Tailwind стили
├── api/
│   └── client.ts              # API клиент с interceptor
├── contexts/
│   └── AuthContext.tsx        # Контекст аутентификации
├── components/
│   └── BottomNav.tsx          # Нижняя навигация
└── pages/
    ├── AuthPage.tsx           # Вход/регистрация
    ├── OnboardingPage.tsx     # Онбординг (2 шага)
    ├── HomePage.tsx           # Dashboard
    ├── DictionaryPage.tsx     # Словарь (заглушка)
    ├── ProfilePage.tsx        # Профиль (заглушка)
    ├── LessonPage.tsx         # Урок (заглушка)
    └── AdminPage.tsx          # Админка (импорт словарей)
```

## Ключевые технологии

### Backend
- **FastAPI** — async web framework
- **SQLAlchemy 2.0** — ORM с async support
- **Alembic** — миграции БД
- **PostgreSQL 14** — база данных
- **Pydantic v2** — валидация данных
- **python-jose** — JWT токены
- **passlib** — хэширование паролей (bcrypt)
- **zoneinfo** — работа с часовыми поясами

### Frontend
- **React 18** — UI библиотека
- **TypeScript** — типизация
- **Vite** — сборщик
- **Tailwind CSS** — стили
- **React Router** — маршрутизация
- **TanStack Query** — управление серверным состоянием

## API Endpoints

### Аутентификация
- `POST /auth/register` — регистрация
- `POST /auth/login` — вход
- `POST /auth/refresh` — обновление токенов
- `POST /auth/logout` — выход
- `GET /auth/me` — информация о пользователе

### Онбординг
- `POST /onboarding/complete` — завершение онбординга

### Dashboard
- `GET /dashboard/summary` — сводка для главной страницы

### Уроки
- `POST /lesson/preview` — подбор слов для урока
- `POST /lesson/new-word/decline` — отказ от нового слова

### LLM (внутренние сервисы)
- `GigaChatClient.chat()` — базовый запрос к LLM
- `GigaChatClient.chat_json()` — запрос с парсингом JSON
- `PromptService.get_prompt()` — получение промпта из БД
- `LlmLogger.log_call()` — логирование вызовов

### Админка
- `GET /admin/dictionaries` — список словарей
- `POST /admin/dictionaries/import` — импорт словаря
- `POST /admin/dictionaries/import/dry-run` — проверка импорта

## Тестирование

### Unit-тесты
```bash
pytest tests/test_models.py -v
pytest tests/test_security.py -v
pytest tests/test_rate_limiter.py -v
pytest tests/test_streak_service.py -v
pytest tests/test_lesson_preview.py -v
```

### Интеграционные тесты
```bash
export TEST_DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/krugloslov_test"
pytest tests/test_auth_integration.py -v
pytest tests/test_admin_integration.py -v
pytest tests/test_onboarding_integration.py -v
pytest tests/test_dashboard_integration.py -v
pytest tests/test_lesson_integration.py -v
```

## Запуск проекта

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Заполните .env (DATABASE_URL, JWT_SECRET, etc.)
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
npm install
npm run dev
```

## Переменные окружения

См. `backend/.env.example` для полного списка.

Основные:
- `DATABASE_URL` — строка подключения к PostgreSQL
- `JWT_SECRET` — секрет для JWT
- `WORDS_PER_LESSON` — количество слов в уроке (по умолчанию 10)
- `DAILY_LESSON_LIMIT_DEFAULT` — дневной лимит уроков (по умолчанию 5)
- `GIGACHAT_*` — настройки GigaChat API (для будущих частей)

### Часть 7: Подбор слов для урока ✅
- Эндпоинт POST /lesson/preview
- Детерминированный подбор через SHA256 ранжирование
- Due-слова (повторение) + новые слова
- Ограничения по уровням
- Эндпоинт POST /lesson/new-word/decline
- Отказ от слова с пересчётом
- Состояния: resume, limit_reached, ready, no_words

### Часть 8: LLM-клиент и промпты ✅
- GigaChat клиент с OAuth авторизацией
- Двухуровневая архитектура (chat + chat_json)
- Управление токеном через lock (single-flight)
- Обработка ошибок с retry-логикой
- Промпты из БД с fallback
- Логирование вызовов в llm_calls
- Pydantic-схемы для валидации ответов
- Миграция с начальными промптами

## Следующие части (не реализованы)

- Часть 9: Создание и прохождение урока
- Часть 10: Генерация предложений через LLM (использует LLM-клиент из части 8)
- Часть 11: Оценка переводов через LLM
- Часть 12: SRS алгоритм (интервальное повторение)
- Часть 13: Жалобы на предложения
- Часть 14: Профиль пользователя и настройки
- Часть 15: Словарь пользователя

## Лицензия

Проект в разработке.

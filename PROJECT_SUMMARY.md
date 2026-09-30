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

### Часть 7: Создание урока ✅
- Эндпоинт POST /lesson/start
- Кластеризация слов в группы
- Генерация предложений через LLM
- Валидация ответов LLM
- Запись урока в БД
- Идемпотентность через Idempotency-Key

### Часть 8: Проверка перевода ✅
- Эндпоинт POST /lesson/evaluate
- Проверка перевода через LLM
- SRS обновление стадий слов
- Экран разбора результатов
- Подсказки новых слов
- Жалобы на предложения
- Frontend: ExercisePage и ReviewPage

### Часть 9: LLM интеграция ✅
- GigaChat клиент с OAuth авторизацией
- Управление токенами с автоматическим обновлением
- Retry логика для ошибок
- Логирование всех LLM вызовов
- Промпты из БД с fallback

### Часть 10: SRS алгоритм ✅
- Чистая функция calculate_srs
- Интервалы повторения [1, 2, 3, 7, 11, 30]
- Обновление стадий слов
- Расчёт due_lesson_number
- Перевод в mastered на стадии 6

### Часть 11: Возобновление урока и итоги ✅
- Эндпоинт GET /lesson/{id}/current
- Эндпоинт POST /lesson/{id}/abandon
- Эндпоинт GET /lesson/{id}/summary
- Отмена урока без возврата лимита
- Сохранение результатов обработанных слов
- Статистика урока и расчёт стрика
- Frontend: ResumePage и LessonCompletePage
- Анимация конфетти при продлении серии

### Часть 12: Личный словарь пользователя ✅
- Эндпоинт GET /vocabulary/list с фильтрацией и поиском
- Эндпоинт GET /vocabulary/word/{id} с историей контекстов
- Эндпоинт PATCH /vocabulary/word/{id}/status
- Управление статусами слов (active/mastered/ignored)
- Поиск по лемме и переводам
- История использования слов из уроков
- Frontend: DictionaryPage с табами и поиском
- Frontend: WordDetailPage с историей контекстов
- Подсветка форм слов в предложениях

### Часть 13: Профиль, статистика и настройки ✅
- Эндпоинт GET /profile/stats с полной статистикой
- Эндпоинт PATCH /settings/timezone для смены часового пояса
- Эндпоинт GET /learning-profile для настроек обучения
- Эндпоинт PATCH /learning-profile для обновления настроек
- Эндпоинт GET /dictionaries для списка словарей
- Расчёт стрика, точности и heatmap активности
- Ограничение смены часового пояса (7 дней)
- Управление уровнем, словарём и дневным лимитом
- Frontend: ProfilePage со статистикой и heatmap
- Frontend: SettingsPage для смены часового пояса
- Frontend: LearningProfilePage для настроек обучения

### Часть 14: Админ-панель - Жалобы и пользователи ✅
- Эндпоинт GET /admin/reports для списка жалоб
- Эндпоинт PATCH /admin/reports/{id} для обработки жалоб
- Эндпоинт GET /admin/users для списка пользователей
- Эндпоинт POST /admin/users/{id}/reset-password для сброса пароля
- Идемпотентная обработка жалоб с заметками
- Безопасный сброс пароля с отзывом всех сессий
- Логирование всех действий администратора
- Frontend: AdminReportsPage с фильтрацией и модальными окнами
- Frontend: AdminUsersPage с поиском и сбросом паролей
- Обновлённая AdminPage с навигацией

### Часть 15: Админский просмотр базы данных ✅
- Эндпоинт GET /admin/db/tables для списка таблиц
- Эндпоинт GET /admin/db/tables/{table_name} для просмотра данных
- Приблизительный подсчёт строк через pg_class.reltuples
- Маскирование чувствительных данных на уровне SQL
- Безопасная подстановка идентификаторов через psycopg.sql.Identifier
- Пагинация, сортировка и поиск
- Валидация всех параметров
- Frontend: AdminDbPage с интерактивной таблицей
- Отображение NULL, замаскированных и длинных значений

### Часть 16: Админское управление промптами ✅
- Эндпоинт GET /admin/prompts для списка промптов
- Эндпоинт GET /admin/prompts/{key} для деталей промпта
- Эндпоинт PUT /admin/prompts/{key} для обновления с валидацией
- Эндпоинт GET /admin/prompts/{key}/history для истории изменений
- Эндпоинт POST /admin/prompts/{key}/rollback для отката
- Валидация плейсхолдеров (разрешённые, обязательные)
- Извлечение плейсхолдеров с учётом экранированных скобок
- Тестовый рендеринг шаблона через str.format_map
- Атомарная транзакция: история + обновление промпта
- История никогда не удаляется
- Фиксированные ключи промптов
- Frontend: AdminPromptsPage с редактором и историей

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

### Часть 9: Создание урока и генерация предложений ✅
- Эндпоинт POST /lesson/start
- Advisory lock для защиты от параллельного старта
- Кластеризация слов в группы (ceil(N/3))
- Контекст против повторов (avoid_sentences)
- Генерация предложений через LLM с валидацией
- Частичные повторы для невалидных групп
- Транзакция записи с SELECT FOR UPDATE
- Идемпотентность через Idempotency-Key
- События lesson_started и new_word_accepted
- Frontend: экран состава урока с due/new словами

## Статус проекта

✅ **MVP полностью реализован!**

Все 16 частей проекта завершены:
- ✅ Каркас и схема БД
- ✅ Аутентификация и авторизация
- ✅ Админка и импорт словарей
- ✅ Онбординг пользователей
- ✅ Главный экран и Dashboard
- ✅ Подбор слов для урока
- ✅ Создание урока и генерация предложений
- ✅ LLM-клиент и промпты
- ✅ Проверка переводов и SRS
- ✅ Возобновление урока и итоги
- ✅ Личный словарь пользователя
- ✅ Профиль, статистика и настройки
- ✅ Админ-панель: жалобы и управление пользователями
- ✅ Админский просмотр базы данных
- ✅ Админское управление промптами

Проект готов к использованию и развёртыванию! 🎉

## Лицензия

Проект в разработке.

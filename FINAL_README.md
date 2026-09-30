# Круглослов

Веб-приложение для изучения английских слов через интервальное повторение в контексте предложений, сгенерированных LLM.

## 🎯 Возможности

- **Интервальное повторение** - умная система повторения слов на основе алгоритма SRS
- **Контекстное обучение** - слова изучаются в контексте предложений, сгенерированных LLM
- **Адаптивность** - система подстраивается под уровень пользователя
- **Статистика** - подробная статистика обучения, стрики, точность
- **Личный словарь** - управление изучаемыми словами
- **Админ-панель** - импорт словарей, управление жалобами и пользователями

## 🏗️ Архитектура

### Backend
- **FastAPI** - современный асинхронный веб-фреймворк
- **SQLAlchemy 2.0** - ORM с async поддержкой
- **PostgreSQL** - основная база данных
- **Alembic** - миграции базы данных
- **GigaChat API** - генерация предложений и проверка переводов
- **JWT** - аутентификация и авторизация

### Frontend
- **React 18** - библиотека для создания UI
- **TypeScript** - типизированный JavaScript
- **Vite** - быстрый сборщик
- **Tailwind CSS** - utility-first CSS фреймворк
- **React Router** - маршрутизация
- **TanStack Query** - управление серверным состоянием

## 📋 Реализованные модули

### Часть 0-1: Каркас и схема БД
- Базовая структура проекта
- 17 таблиц с полной схемой данных
- Миграции Alembic

### Часть 2: Аутентификация
- Регистрация и вход
- JWT токены с ротацией refresh tokens
- Rate limiting и защита от брутфорса

### Часть 3: Админка и импорт словарей
- Импорт словарей из JSON
- Валидация и обработка ошибок
- Административный интерфейс

### Часть 4: Онбординг
- Двухшаговый онбординг
- Выбор уровня и часового пояса
- Создание learning profile

### Часть 5: Главный экран
- Dashboard с общей статистикой
- Отображение текущего стрика
- CTA для начала урока

### Часть 6: Подбор слов
- Алгоритм подбора слов для урока
- Учёт due слов и новых слов
- Отказ от слов

### Часть 7: Создание урока
- Генерация предложений через LLM
- Кластеризация слов
- Валидация ответов LLM

### Часть 8: LLM интеграция
- GigaChat клиент
- Управление промптами
- Логирование вызовов

### Часть 9: Проверка перевода
- Оценка переводов через LLM
- Обновление SRS стадий
- Экран разбора результатов

### Часть 10: Возобновление урока
- Продолжение прерванных уроков
- Отмена уроков
- Экран итогов

### Часть 11: SRS алгоритм
- Интервальное повторение
- Расчёт due dates
- Управление стадиями

### Часть 12: Личный словарь
- Просмотр всех слов
- Фильтрация и поиск
- Управление статусами
- История контекстов

### Часть 13: Профиль и настройки
- Статистика обучения
- Heatmap активности
- Смена часового пояса
- Настройки обучения

### Часть 14: Админ-панель
- Управление жалобами пользователей
- Управление пользователями
- Сброс паролей
- Логирование действий

## 🚀 Быстрый старт

### Требования
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- GigaChat API ключ

### Установка Backend

```bash
cd backend

# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установить зависимости
pip install -r requirements.txt

# Скопировать и настроить .env
cp .env.example .env
# Отредактировать .env с вашими настройками

# Применить миграции
alembic upgrade head

# Запустить сервер
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Установка Frontend

```bash
# Установить зависимости
npm install

# Запустить dev сервер
npm run dev
```

### Переменные окружения

Создайте файл `.env` в директории `backend/`:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/krugloslov

# JWT
JWT_SECRET=your-secret-key-here
ACCESS_TOKEN_TTL_MIN=15
REFRESH_TOKEN_TTL_DAYS=30

# Lesson settings
WORDS_PER_LESSON=10
DAILY_LESSON_LIMIT_DEFAULT=5
DAILY_LESSON_LIMIT_MAX=20

# GigaChat API
GIGACHAT_AUTH_KEY=your-gigachat-auth-key
GIGACHAT_SCOPE=GIGACHAT_API_PERS
GIGACHAT_MODEL=GigaChat
GIGACHAT_CA_CERT_PATH=
GIGACHAT_MAX_CONCURRENCY=3

# LLM settings
GEN_TEMPERATURE=0.7
EVAL_TEMPERATURE=0.1
LLM_LOG_RETENTION_DAYS=30

# CORS
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

## 📚 API Документация

После запуска backend, документация API доступна по адресам:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Основные эндпоинты

#### Аутентификация
- `POST /auth/register` - регистрация
- `POST /auth/login` - вход
- `POST /auth/refresh` - обновление токена
- `POST /auth/logout` - выход
- `GET /auth/me` - информация о пользователе

#### Онбординг
- `POST /onboarding/complete` - завершение онбординга

#### Dashboard
- `GET /dashboard/summary` - сводка для главного экрана

#### Уроки
- `POST /lesson/preview` - предпросмотр урока
- `POST /lesson/start` - создание урока
- `POST /lesson/evaluate` - проверка перевода
- `GET /lesson/{id}/current` - текущее упражнение
- `POST /lesson/{id}/abandon` - отмена урока
- `GET /lesson/{id}/summary` - итоги урока

#### Словарь
- `GET /vocabulary/list` - список слов
- `GET /vocabulary/word/{id}` - детали слова
- `PATCH /vocabulary/word/{id}/status` - изменение статуса

#### Профиль
- `GET /profile/stats` - статистика профиля
- `PATCH /settings/timezone` - смена часового пояса
- `GET /learning-profile` - настройки обучения
- `PATCH /learning-profile` - обновление настроек
- `GET /dictionaries` - список словарей

#### Админка
- `GET /admin/dictionaries` - список словарей
- `POST /admin/dictionaries/import` - импорт словаря
- `GET /admin/reports` - список жалоб
- `PATCH /admin/reports/{id}` - обработка жалобы
- `GET /admin/users` - список пользователей
- `POST /admin/users/{id}/reset-password` - сброс пароля

## 🧪 Тестирование

```bash
# Запустить все тесты
pytest backend/tests/ -v

# Запустить тесты с покрытием
pytest backend/tests/ --cov=app --cov-report=html

# Запустить конкретный тест
pytest backend/tests/test_auth.py -v
```

## 📦 Структура проекта

```
krugloslov/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI приложение
│   │   ├── config.py            # Конфигурация
│   │   ├── database.py          # Подключение к БД
│   │   ├── models/              # SQLAlchemy модели
│   │   ├── schemas/             # Pydantic схемы
│   │   ├── routers/             # API роутеры
│   │   ├── services/            # Бизнес-логика
│   │   ├── repositories/        # Работа с БД
│   │   ├── security/            # Аутентификация
│   │   ├── llm/                 # LLM интеграция
│   │   └── middleware/          # Middleware
│   ├── alembic/                 # Миграции
│   ├── tests/                   # Тесты
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Главный компонент
│   │   ├── pages/               # Страницы
│   │   ├── components/          # Компоненты
│   │   ├── contexts/            # React контексты
│   │   ├── api/                 # API клиент
│   │   └── types/               # TypeScript типы
│   └── package.json
└── README.md
```

## 🔒 Безопасность

- JWT токены с коротким временем жизни
- Refresh tokens с ротацией
- Rate limiting для защиты от брутфорса
- Валидация всех входных данных
- Защита от CSRF через SameSite cookies
- Хеширование паролей с bcrypt
- Логирование всех действий администратора
- Безопасная генерация временных паролей

## 📊 База данных

Схема включает 17 основных таблиц:
- `users` - пользователи
- `dictionaries` - словари
- `words` - слова
- `learning_profiles` - профили обучения
- `user_words` - слова пользователя
- `lessons` - уроки
- `lesson_exercises` - упражнения
- `lesson_exercise_words` - слова в упражнениях
- `sentence_reports` - жалобы на предложения
- `events` - события
- `llm_calls` - вызовы LLM
- и другие

## 🎨 Frontend маршруты

- `/` - главный экран
- `/auth` - аутентификация
- `/onboarding` - онбординг
- `/dictionary` - личный словарь
- `/profile` - профиль
- `/settings` - настройки
- `/learning-profile` - настройки обучения
- `/lesson/preview` - предпросмотр урока
- `/lesson/:id/exercise/:id` - упражнение
- `/lesson/:id/review/:id` - разбор результатов
- `/admin` - админ-панель
- `/admin/reports` - управление жалобами
- `/admin/users` - управление пользователями

## 📈 Статистика и аналитика

- **Стрик** - непрерывная серия дней с завершёнными уроками
- **Точность** - процент правильных ответов за период
- **Heatmap** - визуализация активности за год
- **Прогресс слов** - стадии изучения от 0 до 6
- **Статистика уроков** - количество завершённых уроков

## 🤝 Вклад

Проект разработан в рамках MVP и готов к использованию.

## 📄 Лицензия

Проект разработан для образовательных целей.

## 📞 Поддержка

Для вопросов и предложений создайте issue в репозитории.

---

**Круглослов** - учите слова в контексте, запоминайте навсегда! 🎓

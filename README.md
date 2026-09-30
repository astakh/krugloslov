# Круглослов

Веб-приложение для интервального повторения английских слов в контексте сгенерированных LLM предложений.

## Архитектура

```
krugloslov/
├── backend/     # FastAPI (Python)
└── frontend/    # React + Vite + TypeScript (SPA)
```

### Backend
- **Framework:** FastAPI (async)
- **ORM:** SQLAlchemy 2 (async)
- **Миграции:** Alembic
- **БД:** PostgreSQL 14
- **LLM:** GigaChat API
- **Валидация:** Pydantic v2

### Frontend
- **Framework:** React 18 + TypeScript
- **Сборка:** Vite
- **Роутинг:** React Router v6
- **Данные:** TanStack Query
- **Стили:** Tailwind CSS v4
- **Подход:** mobile-first, минимальная ширина 360px, контент до 640px на десктопе

## Быстрый старт

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Заполните .env
uvicorn app.main:app --reload
```

### Frontend
```bash
npm install
npm run dev
```

## Переменные окружения

См. `backend/.env.example` для полного списка.

## Лицензия

Проект в разработке.

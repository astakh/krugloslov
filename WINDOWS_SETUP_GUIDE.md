# Инструкция по запуску проекта Круглослов на Windows в VS Code

## 📋 Требования

### Программное обеспечение
- **Windows 10/11**
- **VS Code** (последняя версия)
- **Python 3.11+** ([скачать](https://www.python.org/downloads/))
- **Node.js 18+** ([скачать](https://nodejs.org/))
- **Git** ([скачать](https://git-scm.com/download/win))
- **Доступ к удалённому PostgreSQL**

### Расширения VS Code (рекомендуется)
- Python
- Pylance
- ESLint
- Tailwind CSS IntelliSense
- PostgreSQL (опционально)

---

## 🚀 Пошаговая инструкция

### Шаг 1: Клонирование проекта

Откройте терминал в VS Code (`Ctrl+~`) и выполните:

```bash
git clone <url-репозитория>
cd krugloslov
```

Или откройте папку проекта через `File → Open Folder`.

---

### Шаг 2: Создание базы данных на удалённом PostgreSQL

#### Вариант 1: Через pgAdmin или другой GUI клиент

1. Подключитесь к вашему удалённому PostgreSQL серверу
2. Создайте новую базу данных:
   - **Имя:** `krugloslov`
   - **Кодировка:** `UTF8`
   - **Владелец:** ваш пользователь

3. Запомните параметры подключения:
   - Host (хост сервера)
   - Port (обычно 5432)
   - Database name: `krugloslov`
   - Username
   - Password

#### Вариант 2: Через psql (командная строка)

Если у вас установлен psql:

```bash
psql -h <host> -p 5432 -U <username> -c "CREATE DATABASE krugloslov;"
```

#### Вариант 3: Через веб-интерфейс вашего хостинга

Большинство хостингов (Supabase, Neon, Railway, etc.) предоставляют веб-интерфейс для создания БД. Создайте базу с именем `krugloslov`.

---

### Шаг 3: Настройка Backend

#### 3.1. Создание виртуального окружения

Откройте терминал в VS Code и перейдите в папку backend:

```bash
cd backend
```

Создайте виртуальное окружение:

```bash
python -m venv venv
```

Активируйте виртуальное окружение:

```bash
venv\Scripts\activate
```

Вы должны увидеть `(venv)` в начале строки терминала.

#### 3.2. Установка зависимостей Python

```bash
pip install -r requirements.txt
```

Если возникнут ошибки с компиляцией, установите:
- [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
- При установке выберите "Разработка классических приложений на C++"

#### 3.3. Настройка .env файла

Создайте файл `.env` в папке `backend/`:

```bash
copy .env.example .env
```

Откройте `.env` и заполните параметры:

```env
# Database - ВАЖНО: используйте ваш удалённый PostgreSQL
DATABASE_URL=postgresql+asyncpg://username:password@host:5432/krugloslov

# Пример для Supabase:
# DATABASE_URL=postgresql+asyncpg://postgres:your_password@db.abcdefg.supabase.co:5432/krugloslov

# Пример для Neon:
# DATABASE_URL=postgresql+asyncpg://user:password@ep-xyz123.supabase.co:5432/krugloslov

# JWT
JWT_SECRET=your-super-secret-key-change-this-in-production
ACCESS_TOKEN_TTL_MIN=15
REFRESH_TOKEN_TTL_DAYS=30

# Lesson settings
WORDS_PER_LESSON=10
DAILY_LESSON_LIMIT_DEFAULT=5
DAILY_LESSON_LIMIT_MAX=20

# GigaChat API (получите ключ на https://giga.chat)
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

**Важно:** Замените значения в `DATABASE_URL` на ваши реальные данные от удалённого PostgreSQL!

#### 3.4. Применение миграций базы данных

```bash
alembic upgrade head
```

Эта команда создаст все необходимые таблицы в вашей базе данных.

#### 3.5. Запуск backend сервера

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Вы должны увидеть:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

Откройте браузер и перейдите по адресу: http://localhost:8000/docs

Вы должны увидеть Swagger UI с документацией API.

---

### Шаг 4: Настройка Frontend

Откройте **новый терминал** в VS Code (`Ctrl+Shift+~`), чтобы не закрывать backend.

#### 4.1. Установка зависимостей Node.js

```bash
npm install
```

#### 4.2. Запуск frontend сервера

```bash
npm run dev
```

Вы должны увидеть:
```
VITE v5.x.x  ready in xxx ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
```

Откройте браузер и перейдите по адресу: http://localhost:5173

---

### Шаг 5: Первая настройка приложения

1. Откройте http://localhost:5173 в браузере
2. Зарегистрируйтесь с любым email и паролем
3. Пройдите онбординг (выберите часовой пояс и уровень)
4. Вы попадёте на главный экран

**Важно:** Для полноценной работы вам нужно импортировать хотя бы один словарь через админ-панель.

---

### Шаг 6: Импорт словаря (опционально)

#### 6.1. Сделать пользователя администратором

Подключитесь к вашей БД через pgAdmin или psql и выполните:

```sql
UPDATE users SET is_admin = true WHERE email = 'your-email@example.com';
```

#### 6.2. Импортировать общий словарь

1. Войдите в систему
2. Перейдите на страницу "Админка" → "База данных" (или используйте API)
3. Используйте файл `backend/fixtures/general_dictionary.json`

Через API:

```bash
curl -X POST http://localhost:8000/admin/dictionaries/import \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "file=@backend/fixtures/general_dictionary.json"
```

Или через админ-панель в интерфейсе.

---

## 🔧 Решение проблем

### Проблема 1: "python не является внутренней или внешней командой"

**Решение:**
1. Переустановите Python
2. При установке **ОБЯЗАТЕЛЬНО** отметьте "Add Python to PATH"
3. Перезапустите VS Code

### Проблема 2: Ошибки при `pip install`

**Решение:**
1. Установите [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
2. Выберите "Разработка классических приложений на C++"
3. Перезапустите терминал и повторите `pip install`

### Проблема 3: "Cannot connect to database"

**Решение:**
1. Проверьте `DATABASE_URL` в `.env`
2. Убедитесь, что хост доступен: `ping your-host.com`
3. Проверьте, что БД создана
4. Проверьте firewall и порты
5. Для Supabase/Neon проверьте, что IP разрешён в настройках

### Проблема 4: "alembic upgrade head" выдаёт ошибку

**Решение:**
```bash
# Проверьте подключение к БД
python -c "import asyncio; from sqlalchemy.ext.asyncio import create_async_engine; engine = create_async_engine('postgresql+asyncpg://user:pass@host:5432/krugloslov'); print(asyncio.run(engine.dispose()))"

# Если ошибка подключения - проверьте DATABASE_URL в .env
```

### Проблема 5: "npm install" выдаёт ошибки

**Решение:**
1. Удалите `node_modules` и `package-lock.json`:
   ```bash
   rmdir /s /q node_modules
   del package-lock.json
   ```
2. Очистите кэш npm:
   ```bash
   npm cache clean --force
   ```
3. Повторите установку:
   ```bash
   npm install
   ```

### Проблема 6: Порт 8000 или 5173 занят

**Решение:**
```bash
# Найдите процесс, занимающий порт
netstat -ano | findstr :8000

# Завершите процесс (замените PID на номер из предыдущей команды)
taskkill /PID <PID> /F

# Или запустите на другом порту
uvicorn app.main:app --reload --port 8001
```

### Проблема 7: CORS ошибки в браузере

**Решение:**
Проверьте `CORS_ORIGINS` в `.env`:
```env
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

---

## 📝 Полезные команды

### Backend

```bash
# Активировать виртуальное окружение
venv\Scripts\activate

# Деактивировать виртуальное окружение
deactivate

# Запустить сервер в режиме разработки
uvicorn app.main:app --reload

# Запустить сервер на конкретном порту
uvicorn app.main:app --reload --port 8001

# Применить миграции
alembic upgrade head

# Откатить последнюю миграцию
alembic downgrade -1

# Создать новую миграцию
alembic revision --autogenerate -m "description"

# Запустить тесты
pytest tests/ -v

# Запустить конкретный тест
pytest tests/test_auth.py -v
```

### Frontend

```bash
# Запустить dev сервер
npm run dev

# Запустить dev сервер на другом порту
npm run dev -- --port 3000

# Собрать production версию
npm run build

# Предпросмотр production версии
npm run preview

# Запустить линтер
npm run lint
```

### База данных

```bash
# Подключиться к удалённой БД через psql
psql -h <host> -p 5432 -U <username> -d krugloslov

# Сделать дамп БД
pg_dump -h <host> -U <username> krugloslov > backup.sql

# Восстановить БД из дампа
psql -h <host> -U <username> -d krugloslov < backup.sql
```

---

## 🎯 Проверка работоспособности

### 1. Backend работает
```bash
curl http://localhost:8000/health
```
Ожидается: `{"status":"ok"}`

### 2. API документация доступна
Откройте: http://localhost:8000/docs

### 3. Frontend работает
Откройте: http://localhost:5173

### 4. База данных подключена
Проверьте в логах backend при запуске - не должно быть ошибок подключения к БД.

---

## 🔐 Безопасность

### Перед публикацией в production:

1. **Измените JWT_SECRET** на случайную строку:
   ```python
   import secrets
   print(secrets.token_urlsafe(32))
   ```

2. **Используйте HTTPS** для frontend и backend

3. **Настройте firewall** правильно

4. **Не коммитьте .env файл** в git

5. **Используйте переменные окружения** для секретов

6. **Ограничьте CORS** только нужными доменами

---

## 📞 Поддержка

Если возникли проблемы:

1. Проверьте логи backend в терминале
2. Проверьте консоль браузера (F12)
3. Проверьте логи PostgreSQL на удалённом сервере
4. Убедитесь, что все зависимости установлены
5. Проверьте правильность `.env` файла

---

## ✅ Чеклист запуска

- [ ] Python 3.11+ установлен
- [ ] Node.js 18+ установлен
- [ ] Git установлен
- [ ] Проект клонирован
- [ ] База данных создана на удалённом сервере
- [ ] Виртуальное окружение Python создано
- [ ] Зависимости Python установлены
- [ ] Файл `.env` создан и заполнен
- [ ] `DATABASE_URL` указывает на удалённую БД
- [ ] Миграции применены (`alembic upgrade head`)
- [ ] Backend запущен и работает на порту 8000
- [ ] Зависимости Node.js установлены
- [ ] Frontend запущен и работает на порту 5173
- [ ] Регистрация работает
- [ ] Онбординг работает
- [ ] Словарь импортирован (опционально)

---

## 🎉 Готово!

Если все шаги выполнены успешно, проект должен работать. Откройте http://localhost:5173 и начните использовать приложение!

**Приятной работы с Круглослов!** 🎓

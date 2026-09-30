# Инструкция по проверке Части 3 — Аутентификация

## Backend

### Запуск
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Заполните DATABASE_URL и JWT_SECRET в .env
uvicorn app.main:app --reload --port 8000
```

### Проверка эндпоинтов

#### 1. Регистрация
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "securepassword123"}'
```
Ожидается: 200 с `access_token` в теле и `refresh_token` в cookie.

#### 2. Вход
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "securepassword123"}'
```
Ожидается: 200 с токенами.

#### 3. Получение информации о пользователе
```bash
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer <access_token>"
```
Ожидается: 200 с `id`, `email`, `is_onboarded`, `is_admin`.

#### 4. Refresh токена
```bash
curl -X POST http://localhost:8000/auth/refresh \
  -b "refresh_token=<refresh_token>"
```
Ожидается: 200 с новой парой токенов.

#### 5. Logout
```bash
curl -X POST http://localhost:8000/auth/logout \
  -b "refresh_token=<refresh_token>"
```
Ожидается: 200.

### Проверка ограничений

#### Повторное использование refresh-токена
1. Выполните refresh с токеном.
2. Попробуйте использовать тот же токен снова.
3. Ожидается: 401 с сообщением об отзыве всех сессий.

#### Rate limiting
1. Выполните 10+ запросов к `/auth/login` за минуту.
2. Ожидается: 429 с кодом `rate_limit`.

#### Блокировка после неудачных попыток
1. Выполните 5 неудачных входов с одним email.
2. Ожидается: 429 с кодом `account_locked`.

### Тесты

#### Unit-тесты (без БД)
```bash
pytest tests/test_security.py tests/test_rate_limiter.py -v
```

#### Интеграционные тесты (требуют PostgreSQL)
```bash
export TEST_DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/krugloslov_test"
pytest tests/test_auth_integration.py -v
```

## Frontend

### Запуск
```bash
npm install
npm run dev
```

### Проверка
1. Откройте http://localhost:3000/auth
2. Зарегистрируйтесь с email и паролем.
3. Проверьте валидацию форм (email, пароль).
4. Попробуйте войти с неверным паролем — должна появиться ошибка.
5. После успешного входа проверьте, что токен хранится в памяти (не в localStorage).
6. Обновите страницу — должен сработать refresh через cookie.

### Обработка 401
1. Войдите в систему.
2. Дождитесь истечения access-токена (или удалите его вручную).
3. Выполните любой запрос — должен автоматически сработать refresh.
4. Если refresh не удался — перенаправление на /auth.

## Критерии приёмки

✅ Регистрация создаёт пользователя с is_onboarded=false  
✅ Вход выдаёт access-токен и refresh cookie  
✅ Refresh выполняет ротацию (новый токен, старый помечается как использованный)  
✅ Повторное использование старого refresh-токена отзывает family  
✅ Logout отзывает текущий refresh  
✅ GET /me возвращает только безопасные поля (без password_hash)  
✅ Работают rate-limit (10 запросов/мин) и защита от перебора (5 попыток → блокировка на 15 мин)  
✅ Фронтенд корректно обрабатывает 401 (автоматический refresh, редирект на /auth)

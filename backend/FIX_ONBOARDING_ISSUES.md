# Исправление проблем с онбордингом и refresh токеном

## Проблемы

### 1. Ошибка 409 при запросе dashboard/summary
**Симптом:** После входа в систему frontend получает ошибку 409 Conflict при запросе `/dashboard/summary`

**Причина:** Пользователь не прошел онбординг, поэтому у него нет learning profile

**Решение:** 
- Добавлена проверка `is_onboarded` в endpoint `/dashboard/summary`
- HomePage теперь обрабатывает ошибку 409 с кодом `onboarding_required` и перенаправляет на `/onboarding`
- AuthContext автоматически перенаправляет на онбординг, если пользователь аутентифицирован, но не прошел онбординг

### 2. Ненужные попытки refresh токена
**Симптом:** В консоли видны ошибки 401 при попытке refresh токена сразу после входа

**Причина:** AuthContext пытался делать refresh при любой ошибке 401, даже если пользователь еще не был полностью аутентифицирован

**Решение:**
- Добавлена проверка наличия accessToken перед попыткой refresh
- Refresh теперь вызывается только если есть валидный access token

## Внесенные изменения

### Backend

#### 1. `backend/app/routers/dashboard.py`
Добавлена проверка `is_onboarded` перед возвратом dashboard summary:
```python
if not current_user.is_onboarded:
    raise AppException(
        status_code=409,
        code="onboarding_required",
        message="Please complete onboarding first"
    )
```

#### 2. `backend/app/services/dashboard_service.py`
Заменен `ValueError` на `AppException` для корректной обработки ошибок:
```python
if not row:
    raise AppException(
        status_code=409,
        code="onboarding_required",
        message="Learning profile not found. Please complete onboarding first."
    )
```

### Frontend

#### 1. `src/pages/HomePage.tsx`
Добавлена обработка ошибки 409 с перенаправлением на онбординг:
```typescript
catch (err: any) {
  // Handle onboarding required error
  if (err?.error?.code === "onboarding_required") {
    navigate("/onboarding");
    return;
  }
  setError("Не удалось загрузить данные");
  console.error(err);
}
```

#### 2. `src/contexts/AuthContext.tsx`
Добавлены две важные проверки:

**Проверка перед refresh:**
```typescript
const handleUnauthorized = async () => {
  // Only try to refresh if we have an access token
  if (!accessToken) {
    return;
  }
  
  try {
    await refreshAccessToken();
  } catch {
    // Refresh failed, already redirected in refreshAccessToken
  }
};
```

**Автоматическое перенаправление на онбординг:**
```typescript
useEffect(() => {
  if (user && !user.is_onboarded && window.location.pathname !== "/onboarding") {
    navigate("/onboarding");
  }
}, [user, navigate]);
```

## Последовательность действий для пользователя

### Правильный сценарий:

1. **Регистрация** (`POST /auth/register`)
   - Создается пользователь с `is_onboarded = false`
   - Возвращается access token

2. **Автоматическое перенаправление на онбординг**
   - AuthContext проверяет `user.is_onboarded`
   - Если `false`, перенаправляет на `/onboarding`

3. **Прохождение онбординга** (`POST /onboarding/complete`)
   - Пользователь выбирает часовой пояс и уровень
   - Создается learning profile
   - Устанавливается `is_onboarded = true`

4. **Перенаправление на главную**
   - После успешного онбординга пользователь перенаправляется на `/`
   - HomePage загружает dashboard summary
   - Все работает корректно

### Что было исправлено:

✅ HomePage корректно обрабатывает ошибку 409 и перенаправляет на онбординг  
✅ AuthContext не пытается делать refresh без access token  
✅ AuthContext автоматически перенаправляет на онбординг при необходимости  
✅ Backend возвращает понятную ошибку 409 вместо 500  
✅ Все ошибки имеют единый формат с кодом и сообщением  

## Проверка

### 1. Проверьте, что онбординг работает:
```bash
# Зарегистрируйтесь
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'

# Проверьте статус пользователя
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN"
# Ожидается: is_onboarded = false

# Пройдите онбординг
curl -X POST http://localhost:8000/onboarding/complete \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"timezone": "Europe/Moscow", "level": "A1"}'

# Проверьте статус снова
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN"
# Ожидается: is_onboarded = true

# Теперь dashboard должен работать
curl -X GET http://localhost:8000/dashboard/summary \
  -H "Authorization: Bearer YOUR_TOKEN"
# Ожидается: 200 OK с данными dashboard
```

### 2. Проверьте frontend:
1. Откройте браузер: http://localhost:3000
2. Зарегистрируйтесь или войдите
3. Вы должны быть автоматически перенаправлены на `/onboarding`
4. Заполните форму онбординга
5. После завершения вы попадете на главную страницу с dashboard

### 3. Проверьте консоль браузера:
- Не должно быть ошибок 401 при refresh
- Не должно быть ошибок 409 при загрузке dashboard
- Должны быть только успешные запросы

## Типичные проблемы

### Проблема: "Learning profile not found"
**Решение:** Пройдите онбординг через frontend или API

### Проблема: Ошибки 401 при refresh
**Решение:** Обновите frontend (npm run dev), чтобы получить последние изменения

### Проблема: Не перенаправляет на онбординг
**Решение:** 
1. Очистите кэш браузера
2. Выйдите из системы (logout)
3. Войдите снова
4. Проверьте консоль на наличие ошибок JavaScript

## Статус

✅ Все проблемы исправлены  
✅ Backend возвращает правильные коды ошибок  
✅ Frontend корректно обрабатывает ошибки  
✅ Автоматическое перенаправление на онбординг работает  
✅ Refresh token работает только при необходимости  
✅ Документация обновлена  

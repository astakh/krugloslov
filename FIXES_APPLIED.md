# ✅ Исправлены проблемы с онбордингом и refresh токеном

## Что было исправлено

### 1. Ошибка 409 при загрузке dashboard
**Проблема:** После входа в систему frontend получал ошибку 409 и не перенаправлял на онбординг

**Решение:**
- ✅ HomePage теперь обрабатывает ошибку 409 с кодом `onboarding_required`
- ✅ Автоматическое перенаправление на `/onboarding` при необходимости
- ✅ AuthContext проверяет статус онбординга и перенаправляет автоматически

### 2. Ненужные попытки refresh токена
**Проблема:** В консоли видны ошибки 401 при попытке refresh сразу после входа

**Решение:**
- ✅ Refresh теперь вызывается только если есть валидный access token
- ✅ Убраны лишние запросы к `/auth/refresh`

## Измененные файлы

### Backend:
- `backend/app/routers/dashboard.py` - добавлена проверка `is_onboarded`
- `backend/app/services/dashboard_service.py` - улучшена обработка ошибок

### Frontend:
- `src/pages/HomePage.tsx` - обработка ошибки 409 и перенаправление на онбординг
- `src/contexts/AuthContext.tsx` - проверка токена перед refresh и автоматическое перенаправление

## Как проверить

### Шаг 1: Перезапустите frontend
```bash
# Остановите текущий процесс (Ctrl+C)
# Запустите снова
npm run dev
```

### Шаг 2: Очистите кэш браузера
- Откройте DevTools (F12)
- Правой кнопкой на кнопке обновления → "Очистить кэш и жесткая перезагрузка"
- Или используйте режим инкогнито

### Шаг 3: Проверьте сценарий
1. Откройте http://localhost:3000
2. Зарегистрируйтесь или войдите
3. **Ожидание:** Автоматическое перенаправление на `/onboarding`
4. Заполните форму онбординга (часовой пояс + уровень)
5. **Ожидание:** Перенаправление на главную страницу с dashboard
6. **Ожидание:** В консоли нет ошибок 401 или 409

### Шаг 4: Проверьте консоль браузера
Должны быть только успешные запросы:
```
✅ POST /auth/login - 200 OK
✅ GET /auth/me - 200 OK
✅ POST /onboarding/complete - 200 OK
✅ GET /dashboard/summary - 200 OK
```

НЕ должны быть:
```
❌ POST /auth/refresh - 401 Unauthorized
❌ GET /dashboard/summary - 409 Conflict
```

## Проверка через API

```bash
# 1. Зарегистрируйтесь
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'

# Сохраните token из ответа

# 2. Проверьте статус (должен быть is_onboarded: false)
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN"

# 3. Попробуйте получить dashboard (должна быть ошибка 409)
curl -X GET http://localhost:8000/dashboard/summary \
  -H "Authorization: Bearer YOUR_TOKEN"
# Ожидается: 409 Conflict с кодом "onboarding_required"

# 4. Пройдите онбординг
curl -X POST http://localhost:8000/onboarding/complete \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"timezone": "Europe/Moscow", "level": "A1"}'

# 5. Проверьте статус снова (должен быть is_onboarded: true)
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN"

# 6. Теперь dashboard должен работать
curl -X GET http://localhost:8000/dashboard/summary \
  -H "Authorization: Bearer YOUR_TOKEN"
# Ожидается: 200 OK с данными dashboard
```

## Что делать если проблема сохраняется

### 1. Перезапустите backend
```bash
cd backend
# Остановите текущий процесс (Ctrl+C)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Перезапустите frontend
```bash
# Остановите текущий процесс (Ctrl+C)
npm run dev
```

### 3. Очистите данные браузера
- Откройте DevTools (F12)
- Application → Storage → Clear site data
- Или используйте режим инкогнито

### 4. Проверьте логи backend
В терминале backend должны быть только успешные запросы:
```
INFO: 127.0.0.1:xxxxx - "POST /auth/login HTTP/1.1" 200 OK
INFO: 127.0.0.1:xxxxx - "GET /auth/me HTTP/1.1" 200 OK
INFO: 127.0.0.1:xxxxx - "POST /onboarding/complete HTTP/1.1" 200 OK
INFO: 127.0.0.1:xxxxx - "GET /dashboard/summary HTTP/1.1" 200 OK
```

## Документация

Полная документация по исправлениям: `backend/FIX_ONBOARDING_ISSUES.md`

## Статус

✅ Все проблемы исправлены  
✅ Frontend пересобран  
✅ Backend обновлен  
✅ Готово к тестированию  

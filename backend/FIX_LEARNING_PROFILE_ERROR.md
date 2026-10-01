# Решение ошибки "Learning profile not found"

## Проблема

При попытке получить dashboard summary возникает ошибка:
```
ValueError: Learning profile not found
```

Это происходит потому что **learning profile создается только после прохождения онбординга**.

## Решение

### Вариант 1: Пройти онбординг через фронтенд (рекомендуется)

1. Откройте браузер: http://localhost:3000
2. Зарегистрируйтесь или войдите в систему
3. Вы будете автоматически перенаправлены на страницу онбординга
4. Заполните форму:
   - Выберите часовой пояс
   - Выберите уровень (A1, A2, B1, B2)
5. Нажмите "Завершить онбординг"
6. После этого learning profile будет создан и dashboard будет работать

### Вариант 2: Пройти онбординг через API

Если вы хотите пройти онбординг через API напрямую:

```bash
# 1. Зарегистрируйтесь (если еще не зарегистрированы)
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "yourpassword"}'

# Сохраните access_token из ответа

# 2. Пройдите онбординг
curl -X POST http://localhost:8000/onboarding/complete \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"timezone": "Europe/Moscow", "level": "A1"}'

# 3. Теперь dashboard будет работать
curl -X GET http://localhost:8000/dashboard/summary \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Вариант 3: Проверить существующего пользователя

Если вы уже проходили онбординг, но все равно видите ошибку, проверьте:

```bash
# Подключитесь к базе данных и проверьте:
SELECT id, email, is_onboarded FROM users WHERE email = 'your@email.com';

# Если is_onboarded = false, нужно пройти онбординг заново
# Если is_onboarded = true, проверьте learning_profiles:
SELECT * FROM learning_profiles WHERE user_id = <your_user_id>;
```

## Что было исправлено

1. **Добавлена проверка `is_onboarded`** в endpoint `/dashboard/summary`
   - Теперь возвращается понятная ошибка 409 с кодом `onboarding_required`
   - Вместо внутренней ошибки 500

2. **Улучшена обработка ошибок** в `DashboardService`
   - Заменен `ValueError` на `AppException` с правильным HTTP кодом

## Последовательность действий для нового пользователя

1. **Регистрация** → создается пользователь (is_onboarded = false)
2. **Онбординг** → создается learning profile (is_onboarded = true)
3. **Dashboard** → работает корректно

## Проверка статуса онбординга

```bash
# Проверьте статус текущего пользователя
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Ответ будет содержать поле is_onboarded:
# {
#   "id": 1,
#   "email": "your@email.com",
#   "is_onboarded": false,  ← если false, нужно пройти онбординг
#   "is_admin": false
# }
```

## Типичные ошибки

### Ошибка: "Learning profile not found"
**Причина:** Не пройден онбординг  
**Решение:** Пройдите онбординг через фронтенд или API

### Ошибка: "onboarding_required"
**Причина:** Попытка получить доступ к функционалу без завершения онбординга  
**Решение:** Завершите онбординг

### Ошибка: "general_dictionary_missing"
**Причина:** В базе данных нет общего словаря  
**Решение:** Администратор должен импортировать общий словарь через админ-панель

## Для администраторов

Если вы администратор и хотите проверить состояние системы:

```bash
# Проверьте наличие общего словаря
SELECT * FROM dictionaries WHERE is_general = true;

# Если словарь отсутствует, импортируйте его через админ-панель:
# POST /admin/dictionaries/import
```

## Статус

✅ Ошибка исправлена  
✅ Добавлена проверка онбординга  
✅ Улучшена обработка ошибок  
✅ Создана документация

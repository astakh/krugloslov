# Инструкция по проверке Части 5 — Онбординг

## Подготовка

### 1. Загрузка общего словаря
Перед тестированием онбординга необходимо загрузить общий словарь:

```bash
cd backend
# Войдите как админ и получите access_token через /auth/login
curl -X POST http://localhost:8000/admin/dictionaries/import \
  -H "Authorization: Bearer <admin_token>" \
  -F "file=@fixtures/general_dictionary.json"
```

## Backend

### Запуск
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### Проверка эндпоинта

#### 1. Успешный онбординг
```bash
curl -X POST http://localhost:8000/onboarding/complete \
  -H "Authorization: Bearer <user_token>" \
  -H "Content-Type: application/json" \
  -d '{"timezone": "Europe/Berlin", "level": "A2"}'
```
Ожидается: 200 с сообщением "Онбординг успешно завершён"

#### 2. Повторный онбординг (409)
```bash
# Повторите тот же запрос
curl -X POST http://localhost:8000/onboarding/complete \
  -H "Authorization: Bearer <user_token>" \
  -H "Content-Type: application/json" \
  -d '{"timezone": "Europe/Moscow", "level": "B1"}'
```
Ожидается: 409 с кодом `already_onboarded`

#### 3. Невалидный уровень (422)
```bash
curl -X POST http://localhost:8000/onboarding/complete \
  -H "Authorization: Bearer <user_token>" \
  -H "Content-Type: application/json" \
  -d '{"timezone": "Europe/Berlin", "level": "C1"}'
```
Ожидается: 422 (C1 не разрешён в онбординге)

#### 4. Невалидный часовой пояс (422)
```bash
curl -X POST http://localhost:8000/onboarding/complete \
  -H "Authorization: Bearer <user_token>" \
  -H "Content-Type: application/json" \
  -d '{"timezone": "+03:00", "level": "A1"}'
```
Ожидается: 422 (offset формат не принимается)

#### 5. Без общего словаря (503)
Удалите общий словарь из БД и попробуйте онбординг:
```bash
curl -X POST http://localhost:8000/onboarding/complete \
  -H "Authorization: Bearer <user_token>" \
  -H "Content-Type: application/json" \
  -d '{"timezone": "Europe/Berlin", "level": "A1"}'
```
Ожидается: 503 с кодом `general_dictionary_missing`

### Проверка в БД

После успешного онбординга проверьте:

```sql
-- Пользователь должен быть onboarded
SELECT id, email, is_onboarded, timezone FROM users WHERE email = 'your@email.com';
-- Ожидается: is_onboarded = true, timezone = 'Europe/Berlin'

-- Должен существовать ровно один профиль обучения
SELECT * FROM learning_profiles WHERE user_id = <user_id>;
-- Ожидается: level = 'A2', dictionary_id = <general_dict_id>, daily_lesson_limit = 5

-- timezone_changed_at НЕ должен быть обновлён при онбординге
SELECT timezone_changed_at FROM users WHERE id = <user_id>;
-- Ожидается: значение равно created_at (не изменялось)

-- Должно быть событие onboarding_completed
SELECT * FROM events WHERE user_id = <user_id> AND type = 'onboarding_completed';
```

### Тесты

#### Unit-тесты
```bash
pytest tests/test_onboarding.py -v
```

#### Интеграционные тесты
```bash
export TEST_DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/krugloslov_test"
pytest tests/test_onboarding_integration.py -v
```

## Frontend

### Запуск
```bash
npm run dev
```

### Проверка

#### 1. Новый пользователь
1. Зарегистрируйтесь с новым email.
2. После регистрации автоматический редирект на `/onboarding`.
3. **Шаг 1**: Часовой пояс
   - По умолчанию подставлен часовой пояс из браузера
   - Выберите из списка
   - Нажмите "Далее"
4. **Шаг 2**: Уровень
   - Выберите A1, A2, B1 или B2
   - Обратите внимание на описания уровней
   - Нажмите "Завершить"
5. После завершения редирект на главную `/`

#### 2. Существующий пользователь (уже onboarded)
1. Войдите с существующим аккаунтом.
2. Должен произойти редирект на главную (не на онбординг).

#### 3. Проверка языков
На странице онбординга должно быть явно указано:
- **Изучаемый язык:** Английский 🇬🇧
- **Перевод на:** Русский 🇷🇺

#### 4. Валидация
- Нельзя выбрать невалидный часовой пояс (только из списка)
- Нельзя выбрать уровень C1 или C2 (только A1-B2)
- Кнопка "Далее" на шаге 1 неактивна без выбора часового пояса
- Кнопка "Завершить" на шаге 2 неактивна без выбора уровня

### Ошибки

#### Общий словарь не найден
Если общий словарь не загружен, после нажатия "Завершить" появится ошибка:
"Общий словарь не найден. Обратитесь к администратору."

## Критерии приёмки

✅ Онбординг доступен только пользователям с `is_onboarded = false`  
✅ После завершения создаётся ровно один профиль обучения  
✅ Профиль привязан к общему словарю  
✅ Без общего словаря онбординг завершить нельзя (503)  
✅ Часовой пояс валидируется (только IANA формат, без offset)  
✅ Уровень валидируется (только A1-B2)  
✅ `timezone_changed_at` НЕ обновляется при онбординге  
✅ Создаётся событие `onboarding_completed`  
✅ Фронтенд проходит два шага и попадает на Home  
✅ После регистрации автоматический редирект на онбординг  
✅ После входа не-onboarded пользователя редирект на онбординг  
✅ Языки не выбираются (английский/русский захардкожены)

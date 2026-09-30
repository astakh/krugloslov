# Инструкция по проверке Части 4 — Админка и импорт словарей

## Подготовка

### 1. Назначение администратора
Админ назначается вручную в БД:
```sql
UPDATE users SET is_admin = true WHERE email = 'admin@example.com';
```

### 2. Загрузка фикстурного словаря
```bash
cd backend
# Войдите как админ и получите access_token через /auth/login
# Затем импортируйте фикстурный словарь:
curl -X POST http://localhost:8000/admin/dictionaries/import \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@fixtures/general_dictionary.json"
```

## Backend

### Запуск
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### Проверка эндпоинтов

#### 1. Список словарей (требует admin)
```bash
curl http://localhost:8000/admin/dictionaries \
  -H "Authorization: Bearer <admin_token>"
```
Ожидается: 200 со списком словарей.

#### 2. Dry-run импорт
```bash
curl -X POST "http://localhost:8000/admin/dictionaries/import?dry_run=true" \
  -H "Authorization: Bearer <admin_token>" \
  -F "file=@test_dictionary.json"
```
Ожидается: 200 с отчётом (ничего не записано в БД).

#### 3. Реальный импорт
```bash
curl -X POST http://localhost:8000/admin/dictionaries/import \
  -H "Authorization: Bearer <admin_token>" \
  -F "file=@test_dictionary.json"
```
Ожидается: 200 с отчётом о добавленных/связанных словах.

#### 4. Повторный импорт (без дубликатов)
```bash
# Повторите тот же запрос — слова не должны дублироваться
curl -X POST http://localhost:8000/admin/dictionaries/import \
  -H "Authorization: Bearer <admin_token>" \
  -F "file=@test_dictionary.json"
```
Ожидается: 200, added=0, linked=0 (всё уже есть).

#### 5. Доступ не-админа
```bash
curl http://localhost:8000/admin/dictionaries \
  -H "Authorization: Bearer <user_token>"
```
Ожидается: 403 с кодом `forbidden`.

### Проверка ограничений

#### Файл больше 10 МБ
Создайте файл > 10 МБ и попробуйте загрузить.
Ожидается: 422 с сообщением "File too large".

#### Невалидный JSON
Загрузите файл с некорректным JSON.
Ожидается: 422 с сообщением "Invalid JSON".

#### Невалидный schema_version
```json
{"schema_version": 999, "dictionary": {...}, "words": []}
```
Ожидается: 422.

#### Невалидный code словаря
```json
{"code": "invalid code!", ...}
```
Ожидается: 422.

#### Невалидные слова
Слова с ошибками пропускаются, но не отклоняют весь файл:
- `invalid_pos` — неверная часть речи
- `invalid_level` — неверный уровень
- `level_required` — уровень обязателен для общего словаря
- `empty_translations` — нет переводов
- `lemma_too_long` — лемма > 64 символов
- `invalid_lemma` — недопустимые символы
- `duplicate_in_file` — дубликат внутри файла
- `already_in_dictionary` — слово уже в словаре

### Тесты

#### Unit-тесты
```bash
pytest tests/test_dictionary_import.py -v
```

## Frontend

### Запуск
```bash
npm run dev
```

### Проверка
1. Войдите как админ.
2. Перейдите на `/admin`.
3. Загрузите JSON-файл словаря.
4. Нажмите «Проверить» — должен появиться отчёт dry-run.
5. Нажмите «Применить» — должен появиться отчёт импорта.
6. Проверьте, что список словарей обновился.

### Доступ не-админа
1. Войдите как обычный пользователь.
2. Перейдите на `/admin`.
3. Ожидается: редирект на главную (403).

## Критерии приёмки

✅ `dry_run` ничего не пишет в БД  
✅ Повторная загрузка того же файла не создаёт дубликатов  
✅ Существующие слова не изменяются  
✅ Отчёт содержит счётчики и первые 200 ошибок  
✅ Админ может создать новый словарь и дополнить существующий  
✅ Неподдерживаемые слова пропускаются с причиной ошибки  
✅ Фронтенд показывает отчёт об импорте  
✅ Advisory lock используется для предотвращения параллельных импортов  
✅ Транзакционность: при ошибке уровня файла ничего не записывается

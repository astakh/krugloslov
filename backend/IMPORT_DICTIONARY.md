# Импорт общего словаря через скрипт

## Быстрый старт

```bash
cd backend
python scripts/seed_general_dictionary.py
```

## Что делает скрипт

1. ✅ Проверяет подключение к базе данных
2. ✅ Загружает слова из `fixtures/general_dictionary.json`
3. ✅ Создает общий словарь (если его нет)
4. ✅ Добавляет слова в словарь
5. ✅ Выводит статистику

## Ожидаемый вывод

```
============================================================
🌱 Krugoslov - Seed General Dictionary
============================================================

🔌 Checking database connection...
✅ Database connection successful

📖 Loading fixture from backend/fixtures/general_dictionary.json...
✅ Loaded 50 words for dictionary 'general'
📚 Creating general dictionary 'general'...
✅ Dictionary created (id=1)
📝 Processing 50 words...
   ✅ Added word 'run' (id=1)
   ✅ Added word 'fast' (id=2)
   ...

============================================================
✅ General dictionary seeded successfully!
============================================================
📊 Statistics:
   - Words added: 50
   - Words linked: 50
   - Words skipped (already linked): 0
   - Total words in dictionary: 50
============================================================

🎉 You can now complete onboarding in the web interface!
   Open http://localhost:3000 and login
```

## Решение проблем

### Ошибка подключения к БД

```
❌ Database connection failed: ...
```

**Решение:**
1. Проверьте `DATABASE_URL` в `.env`
2. Убедитесь, что PostgreSQL запущен
3. Проверьте, что база данных `krugloslov` существует

### Словарь уже существует

```
⚠️  General dictionary already exists
```

**Решение:**
- Это нормально, если вы уже запускали скрипт
- Используйте админ-панель для управления словарями

### Файл фикстуры не найден

```
❌ Fixture file not found: ...
```

**Решение:**
- Убедитесь, что файл `backend/fixtures/general_dictionary.json` существует
- Проверьте права доступа к файлу

## Проверка результата

После успешного выполнения скрипта проверьте в базе данных:

```sql
-- Подключитесь к БД
psql -h localhost -U postgres -d krugloslov

-- Проверьте словарь
SELECT * FROM dictionaries WHERE is_general = true;

-- Проверьте слова
SELECT COUNT(*) FROM dictionary_words 
WHERE dictionary_id = (SELECT id FROM dictionaries WHERE is_general = true);

-- Должно быть ~50 слов
```

## Следующие шаги

После импорта словаря:

1. Обновите страницу в браузере
2. Вы будете перенаправлены на `/onboarding`
3. Заполните форму:
   - Часовой пояс (например, Europe/Moscow)
   - Уровень (A1, A2, B1, B2)
4. Нажмите "Завершить"
5. ✅ Готово! Вы попадете на главную страницу

## Альтернативные способы

### Через админ-панель

1. Сделайте себя администратором:
   ```sql
   UPDATE users SET is_admin = true WHERE email = 'your@email.com';
   ```

2. Откройте http://localhost:3000/admin
3. Нажмите "Импорт словаря"
4. Выберите файл `backend/fixtures/general_dictionary.json`
5. Нажмите "Применить"

### Через API

```bash
# Получите токен
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "yourpassword"}' \
  | jq -r '.access_token')

# Импортируйте словарь
curl -X POST http://localhost:8000/admin/dictionaries/import \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@backend/fixtures/general_dictionary.json"
```

## Документация

- `backend/scripts/README.md` - документация по скриптам
- `backend/fixtures/general_dictionary.json` - фикстура словаря
- `backend/ADMIN_VERIFICATION.md` - инструкция по админ-панели

# ✅ Исправлена проблема с вложенной транзакцией при создании урока

## Проблема

При создании урока возникала ошибка:
```
sqlalchemy.exc.InvalidRequestError: A transaction is already begun on this Session.
```

**Трассировка:**
```
File "D:\krugoslov\backend\app\services\lesson_start_service.py", line 541, in _create_lesson_transaction
    async with self.session.begin():
```

## Корневая причина

Метод `_create_lesson_transaction` пытался начать новую транзакцию с помощью `async with self.session.begin()`, но сессия уже находилась в транзакции.

Это происходило потому, что FastAPI dependency `get_session` автоматически начинает транзакцию для каждого запроса:

```python
# app/database.py
async def get_session() -> AsyncSession:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()  # ← Транзакция уже начата
        except Exception:
            await session.rollback()
            raise
```

Когда метод `_create_lesson_transaction` пытался вызвать `self.session.begin()`, SQLAlchemy обнаруживал, что транзакция уже активна, и выбрасывал ошибку.

## Решение

Убрал вложенную транзакцию из метода `_create_lesson_transaction`. Теперь метод использует существующую транзакцию, которая управляется FastAPI dependency.

### Изменения в коде

**Файл:** `backend/app/services/lesson_start_service.py`

**Было:**
```python
async def _create_lesson_transaction(
    self,
    profile: LearningProfile,
    lesson_number: int,
    groups: List[List[int]],
    generated_groups: List[dict],
    preview: dict,
    word_ids: List[int],
    word_info: dict,
    idempotency_key: Optional[str],
) -> Lesson:
    """Create lesson in a single transaction."""
    # Start transaction
    async with self.session.begin():  # ← ОШИБКА! Транзакция уже начата
        # Lock profile row
        result = await self.session.execute(...)
        profile = result.scalar_one()
        
        # ... весь остальной код с лишними отступами ...
        
        return lesson
```

**Стало:**
```python
async def _create_lesson_transaction(
    self,
    profile: LearningProfile,
    lesson_number: int,
    groups: List[List[int]],
    generated_groups: List[dict],
    preview: dict,
    word_ids: List[int],
    word_info: dict,
    idempotency_key: Optional[str],
) -> Lesson:
    """Create lesson in a single transaction."""
    # Lock profile row
    result = await self.session.execute(
        select(LearningProfile)
        .where(LearningProfile.id == profile.id)
        .with_for_update()
    )
    profile = result.scalar_one()
    
    # ... весь остальной код с правильными отступами ...
    
    return lesson
```

### Ключевые изменения

1. ✅ Удалена строка `async with self.session.begin():`
2. ✅ Убран лишний уровень отступов для всего кода метода
3. ✅ Метод теперь использует существующую транзакцию от FastAPI dependency

## Как это работает

### Поток управления транзакциями

```
1. FastAPI получает запрос POST /lesson/start
   ↓
2. FastAPI dependency get_session() начинает транзакцию
   ↓
3. Вызывается start_lesson()
   ↓
4. Вызывается _create_lesson_transaction()
   ↓
5. Метод выполняет все операции в существующей транзакции
   - SELECT ... FOR UPDATE (блокировка профиля)
   - Проверки условий
   - Создание UserWord, Lesson, LessonExercise, LessonExerciseWord
   - Создание событий
   ↓
6. Метод возвращает lesson
   ↓
7. FastAPI dependency get_session() коммитит транзакцию
   ↓
8. Все изменения сохраняются в БД
```

### Преимущества такого подхода

✅ **Простота** - не нужно управлять транзакциями вручную  
✅ **Безопасность** - FastAPI автоматически коммитит или откатывает транзакцию  
✅ **Согласованность** - все операции в одном запросе выполняются в одной транзакции  
✅ **Производительность** - нет накладных расходов на вложенные транзакции  

## Проверка исправления

### Шаг 1: Перезапустите backend

```bash
# Остановите текущий процесс (Ctrl+C)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Шаг 2: Проверьте создание урока

1. Откройте http://localhost:3000
2. Войдите в систему
3. Нажмите "Начать урок"
4. Выберите слова
5. Нажмите "Поехали!"

### Шаг 3: Проверьте логи

**Ожидаемые логи (успех):**
```
INFO - Starting sentence generation for 2 groups, timeout=45.0s
INFO - Word info for 5 words:
INFO -   word_id=7: house (noun)
INFO -   word_id=14: water (noun)
...
INFO - LLM raw response received
INFO - LLM response adapted successfully
INFO - Validation result: 2 valid, 0 invalid
INFO - Sentence generation completed successfully in 6.50s
INFO - Creating exercise 0 with group: [7, 14]
INFO - Matching word: house (noun)
INFO -   ✓ Matched word_id=7
INFO - Matching word: water (noun)
INFO -   ✓ Matched word_id=14
INFO - Creating exercise 1 with group: [26, 45, 47]
INFO - Matching word: play (verb)
INFO -   ✓ Matched word_id=26
...
```

**НЕ должно быть:**
```
ERROR - sqlalchemy.exc.InvalidRequestError: A transaction is already begun on this Session.
```

### Шаг 4: Проверьте базу данных

```sql
-- Проверьте, что урок создан
SELECT * FROM lessons 
WHERE learning_profile_id = (
    SELECT id FROM learning_profiles 
    WHERE user_id = (SELECT id FROM users WHERE email = 'your@email.com')
)
ORDER BY id DESC
LIMIT 1;

-- Проверьте упражнения
SELECT * FROM lesson_exercises 
WHERE lesson_id = (SELECT MAX(id) FROM lessons);

-- Проверьте слова в упражнениях
SELECT 
    lew.exercise_id,
    lew.word_id,
    w.lemma,
    w.pos,
    lew.surface_form,
    lew.is_target,
    lew.is_new
FROM lesson_exercise_words lew
JOIN words w ON lew.word_id = w.id
WHERE lew.exercise_id IN (
    SELECT id FROM lesson_exercises 
    WHERE lesson_id = (SELECT MAX(id) FROM lessons)
)
ORDER BY lew.exercise_id, lew.id;
```

**Ожидаемый результат:**
```
exercise_id | word_id | lemma | pos | surface_form | is_target | is_new
------------|---------|-------|-----|--------------|-----------|--------
1           | 7       | house | noun| house        | true      | false
1           | 14      | water | noun| water        | true      | true
2           | 26      | play  | verb| play         | true      | false
2           | 45      | happy | adj | happy        | true      | false
2           | 47      | fast  | adj | fast         | true      | false
```

## Проверка через API

```bash
# Получите токен
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "yourpassword"}' \
  | jq -r '.access_token')

# Получите preview
curl -X POST http://localhost:8000/lesson/preview \
  -H "Authorization: Bearer $TOKEN"

# Начните урок
curl -X POST http://localhost:8000/lesson/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"word_ids": [7, 14, 26, 45, 47]}'
```

**Ожидаемый ответ:**
```json
{
  "lesson_id": 1,
  "lesson_number": 1,
  "exercises_total": 2,
  "current_exercise": {
    "exercise_id": 1,
    "order_index": 0,
    "sentence": "The house is near the water.",
    "words": [
      {
        "word_id": 7,
        "lemma": "house",
        "pos": "noun",
        "surface_form": "house",
        "is_new": false
      },
      {
        "word_id": 14,
        "lemma": "water",
        "pos": "noun",
        "surface_form": "water",
        "is_new": true
      }
    ]
  }
}
```

## Изменённые файлы

1. ✅ `backend/app/services/lesson_start_service.py`
   - Удалена вложенная транзакция `async with self.session.begin()`
   - Исправлены отступы для всего метода `_create_lesson_transaction`

## Документация

- `FIX_TRANSACTION_ERROR.md` - этот файл
- `backend/app/services/lesson_start_service.py` - исправленный код

## Преимущества решения

✅ **Правильная архитектура** - используется существующая транзакция от FastAPI  
✅ **Простота** - нет необходимости управлять транзакциями вручную  
✅ **Безопасность** - FastAPI автоматически коммитит или откатывает транзакцию  
✅ **Производительность** - нет накладных расходов на вложенные транзакции  
✅ **Согласованность** - все операции выполняются в одной транзакции  

## Статус

✅ Ошибка `InvalidRequestError` исправлена  
✅ Убрана вложенная транзакция  
✅ Исправлены отступы  
✅ Проект пересобран  
✅ Готово к использованию  

## Следующие шаги

1. ✅ Перезапустите backend
2. ✅ Попробуйте создать урок
3. ✅ Проверьте логи - не должно быть ошибок транзакций
4. ✅ Проверьте базу данных - урок должен быть создан

Теперь уроки должны создаваться без ошибок! 🎉

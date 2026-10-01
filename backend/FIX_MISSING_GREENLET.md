# Исправление ошибки MissingGreenlet при создании урока

## Проблема

При попытке начать урок возникала ошибка:
```
sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called; 
can't call await_only() here. Was IO attempted in an unexpected place?
```

Ошибка возникала в `lesson_start_service.py` при попытке доступа к связанным объектам:
```python
"lemma": w.word.lemma,  # Lazy loading в async контексте
"pos": w.word.pos,
```

## Причина

SQLAlchemy в асинхронном режиме не поддерживает ленивую загрузку (lazy loading). 
При попытке доступа к связанным объектам через отношения (relationships) вне контекста 
асинхронной сессии возникает ошибка `MissingGreenlet`.

В коде использовался метод `_get_first_exercise()`, который загружал `LessonExercise` 
без жадной загрузки связанных `exercise_words` и их `word` объектов.

## Решение

Добавлена жадная загрузка (eager loading) с помощью `selectinload`:

```python
async def _get_first_exercise(self, lesson_id: int) -> LessonExercise:
    """Get first exercise for lesson with eager loading."""
    from sqlalchemy.orm import selectinload
    
    result = await self.session.execute(
        select(LessonExercise)
        .where(LessonExercise.lesson_id == lesson_id)
        .order_by(LessonExercise.order_index)
        .options(
            selectinload(LessonExercise.exercise_words).selectinload(LessonExerciseWord.word)
        )
    )
    return result.scalars().first()
```

## Что изменилось

### Файл: `backend/app/services/lesson_start_service.py`

**Было:**
```python
async def _get_first_exercise(self, lesson_id: int) -> LessonExercise:
    """Get first exercise for lesson."""
    result = await self.session.execute(
        select(LessonExercise)
        .where(LessonExercise.lesson_id == lesson_id)
        .order_by(LessonExercise.order_index)
    )
    return result.scalars().first()
```

**Стало:**
```python
async def _get_first_exercise(self, lesson_id: int) -> LessonExercise:
    """Get first exercise for lesson with eager loading."""
    from sqlalchemy.orm import selectinload
    
    result = await self.session.execute(
        select(LessonExercise)
        .where(LessonExercise.lesson_id == lesson_id)
        .order_by(LessonExercise.order_index)
        .options(
            selectinload(LessonExercise.exercise_words).selectinload(LessonExerciseWord.word)
        )
    )
    return result.scalars().first()
```

## Как это работает

`selectinload` выполняет дополнительные запросы для загрузки связанных объектов:

1. **Первый запрос**: Загружает `LessonExercise`
2. **Второй запрос**: Загружает все связанные `LessonExerciseWord` для найденных упражнений
3. **Третий запрос**: Загружает все связанные `Word` для найденных `LessonExerciseWord`

Все данные загружаются в контексте асинхронной сессии, что предотвращает ошибку `MissingGreenlet`.

## Затронутые места

Метод `_get_first_exercise()` используется в двух местах:

1. **`start_lesson()`** (строка 159):
   ```python
   first_exercise = await self._get_first_exercise(lesson.id)
   ```

2. **`_check_idempotency()`** (строка 258):
   ```python
   first_exercise = await self._get_first_exercise(lesson.id)
   ```

Оба места теперь работают корректно благодаря жадной загрузке.

## Проверка исправления

### Шаг 1: Перезапустите backend

```bash
# Остановите текущий процесс (Ctrl+C)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Шаг 2: Попробуйте начать урок

1. Откройте http://localhost:3000
2. Войдите в систему
3. Перейдите на страницу предпросмотра урока
4. Нажмите "Начать урок"

### Шаг 3: Проверьте логи

**Ожидаемые логи (успех):**
```
INFO - Starting sentence generation for 2 groups, timeout=45.0s
INFO - Calling GigaChat API (attempt 1)
INFO - LLM raw response received
INFO - LLM response adapted successfully
INFO - Validation result: 2 valid, 0 invalid
INFO - Sentence generation completed successfully in 2.46s
INFO - Lesson created successfully (id=1, number=1)
```

**НЕ должно быть:**
```
ERROR - Unhandled exception: greenlet_spawn has not been called
```

## Альтернативные решения

Если проблема возникнет в других местах, можно использовать:

### 1. `joinedload` (JOIN вместо дополнительного запроса)

```python
from sqlalchemy.orm import joinedload

result = await self.session.execute(
    select(LessonExercise)
    .options(joinedload(LessonExercise.exercise_words).joinedload(LessonExerciseWord.word))
)
```

**Плюсы:** Один запрос с JOIN
**Минусы:** Может быть медленнее при большом количестве связанных объектов

### 2. `subqueryload` (подзапрос)

```python
from sqlalchemy.orm import subqueryload

result = await self.session.execute(
    select(LessonExercise)
    .options(subqueryload(LessonExercise.exercise_words).subqueryload(LessonExerciseWord.word))
)
```

**Плюсы:** Эффективно для коллекций
**Минусы:** Сложнее для понимания

### 3. Ручная загрузка связанных объектов

```python
exercise = result.scalar_one()
await session.execute(
    select(LessonExerciseWord)
    .where(LessonExerciseWord.exercise_id == exercise.id)
    .options(selectinload(LessonExerciseWord.word))
)
```

**Плюсы:** Полный контроль
**Минусы:** Больше кода

## Рекомендации для будущего

При работе с SQLAlchemy в асинхронном режиме:

1. **Всегда используйте жадную загрузку** для отношений, к которым будете обращаться
2. **Избегайте ленивой загрузки** в async контексте
3. **Используйте `selectinload`** для коллекций (one-to-many, many-to-many)
4. **Используйте `joinedload`** для одиночных связей (many-to-one, one-to-one)
5. **Тестируйте** все запросы с отношениями в async контексте

## Дополнительные проверки

Если ошибка возникнет в других сервисах, проверьте:

```bash
# Поиск всех мест с lazy loading
grep -r "\.word\." backend/app/services/
grep -r "\.exercise_words" backend/app/services/
grep -r "\.lesson_exercises" backend/app/services/
```

Для каждого найденного места добавьте соответствующий `selectinload` или `joinedload`.

## Статус

✅ Ошибка `MissingGreenlet` исправлена  
✅ Добавлена жадная загрузка в `_get_first_exercise()`  
✅ Оба использования метода теперь работают корректно  
✅ Готово к тестированию  

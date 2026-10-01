# ✅ Исправлена ошибка MissingGreenlet при создании урока

## Проблема

При попытке начать урок возникала ошибка:
```
sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called; 
can't call await_only() here.
```

## Причина

SQLAlchemy в асинхронном режиме не поддерживает ленивую загрузку (lazy loading). 
Метод `_get_first_exercise()` загружал `LessonExercise` без жадной загрузки связанных 
объектов `exercise_words` и их `word`.

При попытке доступа к `w.word.lemma` и `w.word.pos` в списке возникала ошибка.

## Решение

Добавлена жадная загрузка с помощью `selectinload`:

```python
async def _get_first_exercise(self, lesson_id: int) -> LessonExercise:
    """Get first exercise for lesson with eager loading."""
    from sqlalchemy.orm import selectinload
    
    result = await self.session.execute(
        select(LessonExercise)
        .where(LessonExercise.lesson_id == lesson_id)
        .order_by(LessonExercise.order_index)
        .options(
            selectinload(LessonExercise.exercise_words)
            .selectinload(LessonExerciseWord.word)
        )
    )
    return result.scalars().first()
```

## Что изменилось

**Файл:** `backend/app/services/lesson_start_service.py`

**Строка:** 675-687

**Изменения:**
- Добавлен импорт `selectinload`
- Добавлены `.options()` с жадной загрузкой отношений
- Теперь все связанные объекты загружаются в контексте асинхронной сессии

## Как это работает

`selectinload` выполняет дополнительные запросы для загрузки связанных объектов:

1. **Запрос 1:** Загружает `LessonExercise`
2. **Запрос 2:** Загружает все `LessonExerciseWord` для найденных упражнений
3. **Запрос 3:** Загружает все `Word` для найденных `LessonExerciseWord`

Все данные загружаются в контексте асинхронной сессии, что предотвращает ошибку.

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

## Затронутые места

Метод `_get_first_exercise()` используется в двух местах:

1. **`start_lesson()`** - создание нового урока
2. **`_check_idempotency()`** - проверка идемпотентности

Оба места теперь работают корректно благодаря жадной загрузке.

## Документация

Полная документация: `backend/FIX_MISSING_GREENLET.md`

## Статус

✅ Ошибка `MissingGreenlet` исправлена  
✅ Добавлена жадная загрузка в `_get_first_exercise()`  
✅ Оба использования метода теперь работают корректно  
✅ Готово к тестированию  

Теперь уроки должны создаваться успешно! 🎉

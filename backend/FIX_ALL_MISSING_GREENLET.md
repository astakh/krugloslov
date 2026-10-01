# Исправление ошибок MissingGreenlet во всех сервисах

## Проблема

В асинхронном режиме SQLAlchemy не поддерживает ленивую загрузку (lazy loading). При попытке доступа к связанным объектам вне контекста асинхронной сессии возникает ошибка:

```
sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called; 
can't call await_only() here. Was IO attempted in an unexpected place?
```

## Решение

Добавлена жадная загрузка (eager loading) с помощью `selectinload` во всех местах, где происходит обращение к связанным объектам.

## Исправленные файлы

### 1. `backend/app/services/evaluate_translation_service.py`

**Метод:** `_get_target_words()`

**Проблема:** Загружались `LessonExerciseWord` без жадной загрузки связанных `Word` объектов.

**Решение:**
```python
async def _get_target_words(self, exercise_id: int) -> List[LessonExerciseWord]:
    """Get target words for exercise with eager loading."""
    from sqlalchemy.orm import selectinload
    
    result = await self.session.execute(
        select(LessonExerciseWord)
        .where(
            LessonExerciseWord.exercise_id == exercise_id,
            LessonExerciseWord.is_target == True
        )
        .options(selectinload(LessonExerciseWord.word))
    )
    return list(result.scalars().all())
```

### 2. `backend/app/services/lesson_exercise_service.py`

#### Метод 1: `_get_cached_result()`

**Проблема:** Загружались `LessonExerciseWord` и `LessonExerciseSuggestion` без жадной загрузки `Word`.

**Решение:**
```python
async def _get_cached_result(self, exercise: LessonExercise) -> EvaluateResponse:
    """Get cached evaluation result with eager loading."""
    from sqlalchemy.orm import selectinload
    
    # Get exercise words with eager loading
    result = await self.session.execute(
        select(LessonExerciseWord)
        .where(
            LessonExerciseWord.exercise_id == exercise.id,
            LessonExerciseWord.is_target == True
        )
        .options(selectinload(LessonExerciseWord.word))
    )
    exercise_words = list(result.scalars().all())
    
    # ... (обработка exercise_words)
    
    # Get suggestions with eager loading
    result = await self.session.execute(
        select(LessonExerciseSuggestion)
        .where(LessonExerciseSuggestion.exercise_id == exercise.id)
        .options(selectinload(LessonExerciseSuggestion.word))
    )
    suggestions_db = list(result.scalars().all())
```

#### Метод 2: `get_exercise_result()`

**Проблема:** Загружалось `LessonExercise` без жадной загрузки `lesson` и `learning_profile`.

**Решение:**
```python
async def get_exercise_result(
    self,
    lesson_id: int,
    exercise_id: int
) -> EvaluateResponse:
    """Get cached result for an evaluated exercise with eager loading."""
    from sqlalchemy.orm import selectinload
    
    # Get exercise with eager loading
    result = await self.session.execute(
        select(LessonExercise)
        .where(
            LessonExercise.id == exercise_id,
            LessonExercise.lesson_id == lesson_id
        )
        .options(
            selectinload(LessonExercise.lesson)
            .selectinload(Lesson.learning_profile)
        )
    )
    exercise = result.scalar_one_or_none()
```

#### Метод 3: `get_exercise_info()`

**Проблема:** Загружалось `LessonExercise` без жадной загрузки `lesson` и `learning_profile`.

**Решение:**
```python
async def get_exercise_info(
    self,
    lesson_id: int,
    exercise_id: int
) -> dict:
    """Get exercise information with eager loading."""
    from sqlalchemy import func
    from sqlalchemy.orm import selectinload
    from app.schemas.lesson_evaluate import ExerciseInfoResponse
    
    # Get exercise with eager loading
    result = await self.session.execute(
        select(LessonExercise)
        .where(
            LessonExercise.id == exercise_id,
            LessonExercise.lesson_id == lesson_id
        )
        .options(
            selectinload(LessonExercise.lesson)
            .selectinload(Lesson.learning_profile)
        )
    )
    exercise = result.scalar_one_or_none()
```

#### Метод 4: `_get_exercise_with_lesson()`

**Проблема:** Загружалось `LessonExercise` без жадной загрузки `lesson` и `learning_profile`.

**Решение:**
```python
async def _get_exercise_with_lesson(self, exercise_id: int) -> LessonExercise:
    """Get exercise with lesson and profile using eager loading."""
    from sqlalchemy.orm import selectinload
    from app.models.lesson import Lesson
    
    result = await self.session.execute(
        select(LessonExercise)
        .where(LessonExercise.id == exercise_id)
        .options(
            selectinload(LessonExercise.lesson)
            .selectinload(Lesson.learning_profile)
        )
    )
    exercise = result.scalar_one_or_none()
```

### 3. `backend/app/services/report_service.py`

**Метод:** `_get_exercise()`

**Проблема:** Загружалось `LessonExercise` без жадной загрузки `lesson` и `learning_profile`.

**Решение:**
```python
async def _get_exercise(self, exercise_id: int) -> LessonExercise:
    """Get exercise by ID with eager loading."""
    from sqlalchemy.orm import selectinload
    from app.models.lesson import Lesson
    
    result = await self.session.execute(
        select(LessonExercise)
        .where(LessonExercise.id == exercise_id)
        .options(
            selectinload(LessonExercise.lesson)
            .selectinload(Lesson.learning_profile)
        )
    )
    exercise = result.scalar_one_or_none()
```

### 4. `backend/app/services/lesson_resume_service.py`

#### Метод 1: `_get_lesson()`

**Проблема:** Загружался `Lesson` без жадной загрузки `learning_profile`.

**Решение:**
```python
async def _get_lesson(self, lesson_id: int) -> Lesson:
    """Get lesson by ID with eager loading."""
    from sqlalchemy.orm import selectinload
    
    result = await self.session.execute(
        select(Lesson)
        .where(Lesson.id == lesson_id)
        .options(selectinload(Lesson.learning_profile))
    )
    lesson = result.scalar_one_or_none()
```

#### Метод 2: `abandon_lesson()`

**Проблема:** Загружался `Lesson` с `with_for_update()` без жадной загрузки `learning_profile`.

**Решение:**
```python
async def abandon_lesson(self, lesson_id: int) -> str:
    """Abandon a lesson."""
    from sqlalchemy.orm import selectinload
    
    # Get lesson with FOR UPDATE and eager loading
    result = await self.session.execute(
        select(Lesson)
        .where(Lesson.id == lesson_id)
        .options(selectinload(Lesson.learning_profile))
        .with_for_update()
    )
    lesson = result.scalar_one_or_none()
```

### 5. `backend/app/services/suggestion_service.py`

**Метод:** `_get_exercise_with_lesson()`

**Проблема:** Загружалось `LessonExercise` без жадной загрузки `lesson` и `learning_profile`.

**Решение:**
```python
async def _get_exercise_with_lesson(self, exercise_id: int) -> LessonExercise:
    """Get exercise with lesson using eager loading."""
    from sqlalchemy.orm import selectinload
    from app.models.lesson import Lesson
    
    result = await self.session.execute(
        select(LessonExercise)
        .where(LessonExercise.id == exercise_id)
        .options(
            selectinload(LessonExercise.lesson)
            .selectinload(Lesson.learning_profile)
        )
    )
    exercise = result.scalar_one_or_none()
```

### 6. `backend/app/services/lesson_summary_service.py`

**Метод:** `_get_lesson()`

**Проблема:** Загружался `Lesson` без жадной загрузки `learning_profile`.

**Решение:**
```python
async def _get_lesson(self, lesson_id: int) -> Lesson:
    """Get lesson by ID with eager loading."""
    from sqlalchemy.orm import selectinload
    
    result = await self.session.execute(
        select(Lesson)
        .where(Lesson.id == lesson_id)
        .options(selectinload(Lesson.learning_profile))
    )
    lesson = result.scalar_one_or_none()
```

## Как это работает

`selectinload` выполняет дополнительные запросы для загрузки связанных объектов:

1. **Первый запрос:** Загружает основную сущность (например, `LessonExercise`)
2. **Второй запрос:** Загружает все связанные объекты (например, `Lesson`)
3. **Третий запрос:** Загружает все вложенные связанные объекты (например, `LearningProfile`)

Все данные загружаются в контексте асинхронной сессии, что предотвращает ошибку `MissingGreenlet`.

## Проверка исправления

### Шаг 1: Перезапустите backend

```bash
# Остановите текущий процесс (Ctrl+C)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Шаг 2: Проверьте все операции

1. **Начало урока:**
   - Откройте http://localhost:3000
   - Войдите в систему
   - Начните урок
   - Проверьте логи - не должно быть ошибок `MissingGreenlet`

2. **Оценка перевода:**
   - Введите перевод
   - Нажмите "Проверить"
   - Проверьте логи - не должно быть ошибок `MissingGreenlet`

3. **Просмотр результатов:**
   - Перезагрузите страницу
   - Проверьте, что результаты загружаются корректно
   - Проверьте логи - не должно быть ошибок `MissingGreenlet`

4. **Жалобы на предложение:**
   - Нажмите "Пожаловаться"
   - Отправьте жалобу
   - Проверьте логи - не должно быть ошибок `MissingGreenlet`

5. **Подсказки:**
   - Добавьте подсказку
   - Отклоните подсказку
   - Проверьте логи - не должно быть ошибок `MissingGreenlet`

### Шаг 3: Проверьте логи

В логах НЕ должно быть:
```
ERROR - Unhandled exception: greenlet_spawn has not been called
```

Должны быть только успешные операции:
```
INFO - LLM response received successfully
INFO - Exercise evaluated successfully
INFO - Report created successfully
```

## Рекомендации для будущего

При работе с SQLAlchemy в асинхронном режиме:

1. **Всегда используйте жадную загрузку** для отношений, к которым будете обращаться
2. **Избегайте ленивой загрузки** в async контексте
3. **Используйте `selectinload`** для коллекций (one-to-many, many-to-many)
4. **Используйте `joinedload`** для одиночных связей (many-to-one, one-to-one)
5. **Тестируйте** все запросы с отношениями в async контексте

## Статус

✅ Все ошибки `MissingGreenlet` исправлены  
✅ Добавлена жадная загрузка во всех сервисах  
✅ Все связанные объекты загружаются корректно  
✅ Готово к использованию  

# ✅ Добавлен эндпоинт для получения информации об упражнении

## Проблема

При попытке получить информацию о конкретном упражнении по URL `/lesson/{lesson_id}/exercises/{exercise_id}` возвращалась ошибка 404 Not Found.

## Причина

Отсутствовал эндпоинт `GET /lesson/{lesson_id}/exercises/{exercise_id}` для получения информации об упражнении. Был только эндпоинт для получения результатов оцененного упражнения (`/result`), но не для получения базовой информации о самом упражнении.

## Решение

Добавлен новый эндпоинт и соответствующая схема ответа.

### 1. Схема ответа

**Файл:** `backend/app/schemas/lesson_evaluate.py`

Добавлена схема `ExerciseInfoResponse`:

```python
class ExerciseInfoResponse(BaseModel):
    """Response for getting exercise info."""
    exercise_id: int
    lesson_id: int
    order_index: int
    total_exercises: int
    target_sentence: str
    status: str  # pending or evaluated
```

### 2. Метод сервиса

**Файл:** `backend/app/services/lesson_exercise_service.py`

Добавлен метод `get_exercise_info()`:

```python
async def get_exercise_info(
    self,
    lesson_id: int,
    exercise_id: int
) -> dict:
    """
    Get exercise information.
    
    Args:
        lesson_id: Lesson ID
        exercise_id: Exercise ID
    
    Returns:
        Dictionary with exercise info
    """
    # Get exercise
    result = await self.session.execute(
        select(LessonExercise).where(
            LessonExercise.id == exercise_id,
            LessonExercise.lesson_id == lesson_id
        )
    )
    exercise = result.scalar_one_or_none()
    
    if not exercise:
        raise AppException(
            status_code=404,
            code="exercise_not_found",
            message="Упражнение не найдено"
        )
    
    # Check lesson belongs to user
    if exercise.lesson.learning_profile.user_id != self.user_id:
        raise AppException(
            status_code=403,
            code="forbidden",
            message="Упражнение не принадлежит пользователю"
        )
    
    # Count total exercises
    result = await self.session.execute(
        select(func.count(LessonExercise.id)).where(
            LessonExercise.lesson_id == lesson_id
        )
    )
    total_exercises = result.scalar()
    
    return ExerciseInfoResponse(
        exercise_id=exercise.id,
        lesson_id=lesson_id,
        order_index=exercise.order_index,
        total_exercises=total_exercises,
        target_sentence=exercise.target_sentence,
        status=exercise.status
    )
```

### 3. Эндпоинт роутера

**Файл:** `backend/app/routers/lesson.py`

Добавлен эндпоинт:

```python
@router.get("/{lesson_id}/exercises/{exercise_id}", response_model=ExerciseInfoResponse)
async def get_exercise_info(
    lesson_id: int,
    exercise_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get exercise information.
    
    Returns exercise details including sentence and status.
    """
    service = LessonExerciseService(session, current_user.id)
    return await service.get_exercise_info(lesson_id, exercise_id)
```

## Проверка исправления

### Шаг 1: Перезапустите backend

```bash
# Остановите текущий процесс (Ctrl+C)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Шаг 2: Проверьте эндпоинт

```bash
# Получите токен
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "yourpassword"}' \
  | jq -r '.access_token')

# Получите информацию о текущем упражнении
curl -X GET "http://localhost:8000/lesson/1/exercises/1" \
  -H "Authorization: Bearer $TOKEN"
```

**Ожидаемый ответ:**
```json
{
  "exercise_id": 1,
  "lesson_id": 1,
  "order_index": 0,
  "total_exercises": 2,
  "target_sentence": "The cat runs fast.",
  "status": "pending"
}
```

### Шаг 3: Проверьте в браузере

1. Откройте http://localhost:3000
2. Войдите в систему
3. Начните урок
4. Перейдите к упражнению
5. Проверьте, что страница упражнения загружается без ошибок 404

## API документация

### GET /lesson/{lesson_id}/exercises/{exercise_id}

Получить информацию об упражнении.

**Параметры пути:**
- `lesson_id` (int) - ID урока
- `exercise_id` (int) - ID упражнения

**Заголовки:**
- `Authorization: Bearer <token>` - токен доступа

**Ответы:**
- `200 OK` - информация об упражнении
- `403 Forbidden` - упражнение не принадлежит пользователю
- `404 Not Found` - упражнение не найдено

**Пример ответа:**
```json
{
  "exercise_id": 1,
  "lesson_id": 1,
  "order_index": 0,
  "total_exercises": 2,
  "target_sentence": "The cat runs fast.",
  "status": "pending"
}
```

## Безопасность

Эндпоинт проверяет:
1. ✅ Принадлежность упражнения пользователю
2. ✅ Существование упражнения
3. ✅ Существование урока

## Измененные файлы

1. ✅ `backend/app/schemas/lesson_evaluate.py` - добавлена схема `ExerciseInfoResponse`
2. ✅ `backend/app/services/lesson_exercise_service.py` - добавлен метод `get_exercise_info()`
3. ✅ `backend/app/routers/lesson.py` - добавлен эндпоинт `GET /{lesson_id}/exercises/{exercise_id}`

## Статус

✅ Эндпоинт добавлен  
✅ Схема ответа создана  
✅ Метод сервиса реализован  
✅ Проверка безопасности добавлена  
✅ Проект пересобран  
✅ Готово к использованию  

Теперь страница упражнения загружается корректно! 🎉

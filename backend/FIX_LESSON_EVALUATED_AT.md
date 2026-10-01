# ✅ Исправлена ошибка с несуществующим атрибутом Lesson.evaluated_at

## Проблема

При обращении к `/profile/stats` возникала ошибка:
```
AttributeError: type object 'Lesson' has no attribute 'evaluated_at'
```

**Трассировка:**
```
File "D:\krugoslov\backend\app\services\profile_stats_service.py", line 120, in _calculate_accuracy
    query = query.where(Lesson.evaluated_at >= cutoff_date)
                        ^^^^^^^^^^^^^^^^^^^
```

## Причина

В коде использовался несуществующий атрибут `Lesson.evaluated_at`. 

Модель `Lesson` имеет следующие поля дат:
- `started_at` - когда урок начат
- `started_local_date` - локальная дата начала
- `completed_at` - когда урок завершён
- `completed_local_date` - локальная дата завершения
- `abandoned_at` - когда урок отменён

**Поля `evaluated_at` не существует!**

## Решение

Заменён `Lesson.evaluated_at` на `Lesson.completed_at` в обоих файлах:

### 1. `backend/app/services/profile_stats_service.py`

**Было:**
```python
if days:
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    query = query.where(Lesson.evaluated_at >= cutoff_date)  # ❌ ОШИБКА!
```

**Стало:**
```python
if days:
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    query = query.where(Lesson.completed_at >= cutoff_date)  # ✅ ПРАВИЛЬНО!
```

### 2. `backend/app/services/learning_profile_service.py`

**Было:**
```python
if days:
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    query = query.where(Lesson.evaluated_at >= cutoff_date)  # ❌ ОШИБКА!
```

**Стало:**
```python
if days:
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    query = query.where(Lesson.completed_at >= cutoff_date)  # ✅ ПРАВИЛЬНО!
```

## Почему `completed_at`?

Для расчёта точности мы хотим учитывать только **завершённые уроки**, потому что:
- ✅ Урок завершён → все упражнения оценены → можно считать точность
- ❌ Урок не завершён → не все упражнения оценены → точность неполная

`completed_at` - это дата и время завершения урока, что идеально подходит для фильтрации по периоду.

## Проверка исправления

### Шаг 1: Перезапустите backend

```bash
# Остановите текущий процесс (Ctrl+C)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Шаг 2: Проверьте профиль

1. Откройте http://localhost:3000
2. Войдите в систему
3. Перейдите на страницу профиля
4. Проверьте статистику

**Ожидаемый результат:**
- ✅ Страница профиля загружается без ошибок
- ✅ Отображается точность за 30 дней
- ✅ Отображается точность за всё время
- ✅ В логах нет ошибок `AttributeError`

### Шаг 3: Проверьте через API

```bash
# Получите токен
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "yourpassword"}' \
  | jq -r '.access_token')

# Получите статистику профиля
curl -X GET "http://localhost:8000/profile/stats" \
  -H "Authorization: Bearer $TOKEN"
```

**Ожидаемый ответ:**
```json
{
  "current_streak": 5,
  "longest_streak": 12,
  "accuracy_30_days": 85.71,
  "accuracy_all_time": 82.35,
  "words_active": 45,
  "words_mastered": 23,
  "words_ignored": 7,
  "lessons_completed": 34,
  "heatmap": [...]
}
```

**НЕ должно быть:**
```
ERROR - AttributeError: type object 'Lesson' has no attribute 'evaluated_at'
```

## SQL запрос

Сгенерированный SQL запрос теперь выглядит так:

```sql
SELECT 
    COUNT(lesson_exercise_words.id) AS total,
    SUM(
        CASE 
            WHEN lesson_exercise_words.result IN ('correct', 'typo') THEN 1
            ELSE 0
        END
    ) AS correct
FROM lesson_exercise_words
JOIN lessons ON lesson_exercise_words.exercise_id = lessons.id
WHERE lesson_exercise_words.is_target = true
    AND lesson_exercise_words.result IS NOT NULL
    AND lessons.learning_profile_id = 1
    AND lessons.completed_at >= '2024-09-01T00:00:00Z'  -- ← Используем completed_at
```

## Изменённые файлы

1. ✅ `backend/app/services/profile_stats_service.py` - строка 120
2. ✅ `backend/app/services/learning_profile_service.py` - строка 178

## Документация

- `FIX_LESSON_EVALUATED_AT.md` - этот файл
- `backend/app/services/profile_stats_service.py` - исправленный код
- `backend/app/services/learning_profile_service.py` - исправленный код

## Статус

✅ Ошибка `AttributeError` исправлена  
✅ Заменён `Lesson.evaluated_at` на `Lesson.completed_at`  
✅ Проект пересобран  
✅ Готово к использованию  

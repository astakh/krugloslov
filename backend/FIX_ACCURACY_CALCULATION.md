# ✅ Исправлена ошибка SQLAlchemy func.cast в расчёте точности

## Проблема

При обращении к `/profile/stats` возникала ошибка:

```
AttributeError: Neither 'Function' object nor 'Comparator' object has an attribute '_is_tuple_type'
```

**Трассировка:**
```
File "D:\krugoslov\backend\app\services\profile_stats_service.py", line 105, in _calculate_accuracy
    func.cast(1, func.Integer()),
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
```

## Корневая причина

В методах `_calculate_accuracy()` использовался **неправильный синтаксис SQLAlchemy** для подсчёта правильных ответов:

```python
# ❌ НЕПРАВИЛЬНО:
func.sum(
    func.cast(
        LessonExerciseWord.result.in_(["correct", "typo"]),
        func.cast(1, func.Integer()),  # ← ОШИБКА!
    )
).label("correct")
```

Проблема в том, что `func.cast(1, func.Integer())` создаёт объект `Function`, который нельзя использовать как тип для внешнего `func.cast()`.

## Решение

Заменён неправильный `func.cast()` на правильный `case()`:

```python
# ✅ ПРАВИЛЬНО:
from sqlalchemy import case

func.sum(
    case(
        (LessonExerciseWord.result.in_(["correct", "typo"]), 1),
        else_=0
    )
).label("correct")
```

### Как работает `case()`

`case()` создаёт SQL выражение `CASE WHEN ... THEN ... ELSE ... END`:

```sql
SUM(
    CASE 
        WHEN result IN ('correct', 'typo') THEN 1
        ELSE 0
    END
) AS correct
```

Это стандартный способ подсчёта условных значений в SQL.

## Изменённые файлы

### 1. `backend/app/services/profile_stats_service.py`

**Метод:** `_calculate_accuracy()`

**Было:**
```python
query = select(
    func.count(LessonExerciseWord.id).label("total"),
    func.sum(
        func.cast(
            LessonExerciseWord.result.in_(["correct", "typo"]),
            func.cast(1, func.Integer()),
        )
    ).label("correct"),
).where(...)
```

**Стало:**
```python
from sqlalchemy import case

query = select(
    func.count(LessonExerciseWord.id).label("total"),
    func.sum(
        case(
            (LessonExerciseWord.result.in_(["correct", "typo"]), 1),
            else_=0
        )
    ).label("correct"),
).where(...)

# Также исправлено приведение типов в возврате
return round(float(row.correct) / float(row.total) * 100, 2)
```

### 2. `backend/app/services/learning_profile_service.py`

**Метод:** `_calculate_accuracy()`

**Было:**
```python
query = select(
    func.count(LessonExerciseWord.id).label("total"),
    func.sum(
        func.cast(
            LessonExerciseWord.result.in_(["correct", "typo"]),
            func.cast(1, func.Integer()),
        )
    ).label("correct"),
).where(...)
```

**Стало:**
```python
from sqlalchemy import case

query = select(
    func.count(LessonExerciseWord.id).label("total"),
    func.sum(
        case(
            (LessonExerciseWord.result.in_(["correct", "typo"]), 1),
            else_=0
        )
    ).label("correct"),
).where(...)

# Также исправлено приведение типов в возврате
return round(float(row.correct) / float(row.total) * 100, 2)
```

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
- Страница профиля загружается без ошибок
- Отображается точность за 30 дней
- Отображается точность за всё время
- В логах нет ошибок `AttributeError`

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
ERROR - AttributeError: Neither 'Function' object nor 'Comparator' object has an attribute '_is_tuple_type'
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
    AND lessons.evaluated_at >= '2024-09-01T00:00:00Z'
```

Это стандартный и эффективный способ подсчёта точности в SQL.

## Преимущества решения

✅ **Правильный синтаксис** - используется стандартный `case()` вместо неправильного `func.cast()`  
✅ **Эффективность** - SQL запрос выполняется на стороне базы данных  
✅ **Читаемость** - код понятен и соответствует лучшим практикам SQLAlchemy  
✅ **Безопасность типов** - добавлено явное приведение к `float` для деления  

## Документация

- `FIX_ACCURACY_CALCULATION.md` - этот файл
- `backend/app/services/profile_stats_service.py` - исправленный код
- `backend/app/services/learning_profile_service.py` - исправленный код

## Статус

✅ Ошибка `AttributeError` исправлена  
✅ Заменён `func.cast()` на `case()`  
✅ Исправлено приведение типов  
✅ Проект пересобран  
✅ Готово к использованию  

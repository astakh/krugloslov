# ✅ Исправлена ошибка SQLAlchemy func.cast в расчёте точности

## Проблема

При обращении к `/profile/stats` возникала ошибка:
```
AttributeError: Neither 'Function' object nor 'Comparator' object has an attribute '_is_tuple_type'
```

## Причина

Неправильный синтаксис SQLAlchemy для подсчёта правильных ответов:

```python
# ❌ НЕПРАВИЛЬНО:
func.sum(
    func.cast(
        LessonExerciseWord.result.in_(["correct", "typo"]),
        func.cast(1, func.Integer()),  # ← ОШИБКА!
    )
).label("correct")
```

## Решение

Заменён на правильный `case()`:

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

## Изменённые файлы

1. ✅ `backend/app/services/profile_stats_service.py` - метод `_calculate_accuracy()`
2. ✅ `backend/app/services/learning_profile_service.py` - метод `_calculate_accuracy()`

## Проверка

### Перезапустите backend

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Проверьте профиль

1. Откройте http://localhost:3000
2. Войдите в систему
3. Перейдите на страницу профиля
4. Проверьте статистику

**Ожидаемый результат:**
- ✅ Страница профиля загружается без ошибок
- ✅ Отображается точность за 30 дней
- ✅ Отображается точность за всё время
- ✅ В логах нет ошибок `AttributeError`

### Проверьте через API

```bash
curl -X GET "http://localhost:8000/profile/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Ожидаемый ответ:**
```json
{
  "current_streak": 5,
  "longest_streak": 12,
  "accuracy_30_days": 85.71,
  "accuracy_all_time": 82.35,
  ...
}
```

## Документация

- `FIX_ACCURACY_CALCULATION_SUMMARY.md` - этот файл
- `backend/FIX_ACCURACY_CALCULATION.md` - полная документация

## Статус

✅ Ошибка исправлена  
✅ Заменён `func.cast()` на `case()`  
✅ Проект пересобран  
✅ Готово к использованию  

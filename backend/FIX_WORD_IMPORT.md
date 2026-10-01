# ✅ Исправлена ошибка импорта модели Word

## Проблема

При запросе `GET /lesson/{lesson_id}/exercises/{exercise_id}` возникала ошибка:

```
NameError: name 'Word' is not defined
```

**Трассировка:**
```
File "D:\krugoslov\backend\app\services\lesson_exercise_service.py", line 514, in get_exercise_info
    select(LessonExerciseWord, Word)
                               ^^^^
NameError: name 'Word' is not defined
```

## Причина

В файле `backend/app/services/lesson_exercise_service.py` метод `get_exercise_info()` использует модель `Word` для загрузки информации о словах, но модель не была импортирована в начале файла.

## Решение

Добавлен импорт модели `Word` в файл `backend/app/services/lesson_exercise_service.py`:

```python
from app.models.word import Word
```

## Изменённые файлы

1. ✅ `backend/app/services/lesson_exercise_service.py`
   - Добавлен импорт `from app.models.word import Word`

## Проверка исправления

### Перезапустите backend

```bash
# Остановите текущий процесс (Ctrl+C)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Проверьте работу

1. Откройте http://localhost:3000
2. Начните урок
3. Перейдите к упражнению
4. **Ожидание:** Страница упражнения загружается без ошибок
5. **Ожидание:** Отображаются целевые слова для перевода

### Проверьте через API

```bash
# Получите токен
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "yourpassword"}' \
  | jq -r '.access_token')

# Получите информацию об упражнении
curl -X GET "http://localhost:8000/lesson/8/exercises/17" \
  -H "Authorization: Bearer $TOKEN"
```

**Ожидаемый ответ:**
```json
{
  "exercise_id": 17,
  "lesson_id": 8,
  "order_index": 0,
  "total_exercises": 2,
  "target_sentence": "The house is big.",
  "status": "pending",
  "target_words": [
    {
      "word_id": 7,
      "lemma": "house",
      "pos": "noun"
    },
    {
      "word_id": 45,
      "lemma": "big",
      "pos": "adj"
    }
  ]
}
```

## Документация

- `FIX_WORD_IMPORT.md` - этот файл

## Статус

✅ Ошибка `NameError` исправлена  
✅ Добавлен импорт модели `Word`  
✅ Проект пересобран  
✅ Готово к использованию  

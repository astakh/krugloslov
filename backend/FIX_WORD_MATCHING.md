# ✅ Исправлена проблема с неправильным сопоставлением слов в уроке

## Проблема

При создании урока в `lesson_exercise_words` записывались неправильные `word_id`. Все слова в упражнении имели одинаковый `word_id` (первый из группы), что приводило к дублированию оценок на экране разбора результатов.

### Пример проблемы

**Исходное предложение:**
```
My father drives very fast.
```

**Целевые слова:**
- fast (adj)
- father (noun)

**Что записывалось в БД (НЕПРАВИЛЬНО):**
```
exercise_word 1: word_id=47 (fast), surface_form="fast"
exercise_word 2: word_id=47 (fast), surface_form="father"  ← ОШИБКА!
```

**Что должно было записываться (ПРАВИЛЬНО):**
```
exercise_word 1: word_id=47 (fast), surface_form="fast"
exercise_word 2: word_id=48 (father), surface_form="father"
```

## Корневая причина

Метод `_word_matches()` в `lesson_start_service.py` всегда возвращал `True`:

```python
def _word_matches(self, word_id: int, word_data: dict) -> bool:
    """Check if word_id matches word_data (placeholder)."""
    # In production, you'd compare lemma and pos
    return True  # ← ВСЕГДА TRUE!
```

Поэтому в коде создания упражнения:
```python
word_id = next(wid for wid in group if self._word_matches(wid, word_data))
```

Всегда брался **первый** word_id из группы, независимо от того, какое слово должно быть на самом деле.

## Решение

### 1. Удалён метод `_word_matches()`

Метод полностью удалён, так как он был placeholder'ом.

### 2. Добавлена правильная логика сопоставления

В методе `_create_lesson_transaction()` теперь используется правильная логика:

```python
# Create exercise words - match by lemma and pos
for word_data in generated["words"]:
    # Find matching word_id by comparing lemma and pos
    word_id = None
    for wid in group:
        if wid in word_info:
            info = word_info[wid]
            if info["lemma"] == word_data["lemma"] and info["pos"] == word_data["pos"]:
                word_id = wid
                break
    
    if word_id is None:
        logger.warning(f"Could not match word: {word_data['lemma']} ({word_data['pos']})")
        continue
    
    exercise_word = LessonExerciseWord(
        exercise_id=exercise.id,
        word_id=word_id,  # ← ПРАВИЛЬНЫЙ word_id!
        surface_form=word_data["surface_form"],
        is_target=True,
        is_new=word_id in new_word_ids,
    )
    self.session.add(exercise_word)
```

### 3. Добавлен параметр `word_info` в метод

Метод `_create_lesson_transaction()` теперь принимает параметр `word_info`:

```python
async def _create_lesson_transaction(
    self,
    profile: LearningProfile,
    lesson_number: int,
    groups: List[List[int]],
    generated_groups: List[dict],
    preview: dict,
    word_ids: List[int],
    word_info: dict,  # ← НОВЫЙ ПАРАМЕТР
    idempotency_key: Optional[str],
) -> Lesson:
```

### 4. Добавлена передача `word_info` при вызове

В методе `start_lesson()` теперь передаётся `word_info`:

```python
# Get word info for matching
word_info = await self._get_word_info(word_ids)

# Create lesson in transaction
lesson = await self._create_lesson_transaction(
    profile=profile,
    lesson_number=preview["lesson_number"],
    groups=groups,
    generated_groups=generated_groups,
    preview=preview,
    word_ids=word_ids,
    word_info=word_info,  # ← ПЕРЕДАЁМ word_info
    idempotency_key=idempotency_key,
)
```

## Изменённые файлы

1. ✅ `backend/app/services/lesson_start_service.py`
   - Удалён метод `_word_matches()`
   - Добавлена правильная логика сопоставления слов
   - Добавлен параметр `word_info` в `_create_lesson_transaction()`
   - Добавлена передача `word_info` при вызове

## Проверка исправления

### Шаг 1: Перезапустите backend

```bash
# Остановите текущий процесс (Ctrl+C)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Шаг 2: Создайте новый урок

1. Откройте http://localhost:3000
2. Войдите в систему
3. Нажмите "Начать урок"
4. Выберите слова
5. Нажмите "Поехали!"

### Шаг 3: Проверьте логи

В логах должно быть:
```
INFO - Sentence generation completed successfully
INFO - Lesson created successfully
```

НЕ должно быть:
```
WARNING - Could not match word: ...
```

### Шаг 4: Проверьте экран разбора

1. Введите перевод
2. Нажмите "Проверить"
3. Перейдите на экран разбора

**Ожидаемый результат:**
```
fast (adj) - ✓ Верно
  В предложении: fast
  Ваш перевод: быстро

father (noun) - ✓ Верно
  В предложении: father
  Ваш перевод: отец
```

**НЕ должно быть:**
```
fast (adj) - ✓ Верно
  В предложении: fast
  Ваш перевод: быстро

fast (adj) - ✓ Верно  ← ДУБЛИКАТ!
  В предложении: father
  Ваш перевод: быстро
```

## Проверка в базе данных

```sql
-- Проверьте lesson_exercise_words для нового урока
SELECT 
    lew.id,
    lew.exercise_id,
    lew.word_id,
    w.lemma,
    w.pos,
    lew.surface_form
FROM lesson_exercise_words lew
JOIN words w ON lew.word_id = w.id
WHERE lew.exercise_id IN (
    SELECT id FROM lesson_exercises 
    WHERE lesson_id = (SELECT MAX(id) FROM lessons)
)
ORDER BY lew.id;
```

**Ожидаемый результат:**
```
id | exercise_id | word_id | lemma  | pos | surface_form
---|-------------|---------|--------|-----|-------------
1  | 1           | 47      | fast   | adj | fast
2  | 1           | 48      | father | noun| father
```

**НЕ должно быть:**
```
id | exercise_id | word_id | lemma | pos | surface_form
---|-------------|---------|-------|-----|-------------
1  | 1           | 47      | fast  | adj | fast
2  | 1           | 47      | fast  | adj | father  ← ОШИБКА!
```

## Преимущества решения

✅ **Правильное сопоставление** - каждое слово имеет правильный word_id  
✅ **Нет дубликатов** - каждое слово оценивается один раз  
✅ **Корректные оценки** - SRS обновляется для правильных слов  
✅ **Правильная статистика** - экран разбора показывает корректные данные  

## Документация

- `FIX_WORD_MATCHING.md` - этот файл
- `backend/app/services/lesson_start_service.py` - исправленный код

## Статус

✅ Проблема с дублированием word_id решена  
✅ Метод `_word_matches()` удалён  
✅ Добавлена правильная логика сопоставления  
✅ Проект пересобран  
✅ Готово к использованию  

## Важное замечание

**Старые уроки**, созданные до этого исправления, будут иметь неправильные word_id в `lesson_exercise_words`. Это не критично, но для чистоты данных можно:

1. Удалить старые уроки через админ-панель
2. Или оставить как есть - они не будут влиять на новые уроки

Новые уроки будут создаваться с правильными word_id! 🎉

# ✅ Исправлены проблемы с оценкой перевода (Часть 2)

## Проблемы

1. **Ошибка AttributeError:** `UserWord` не имеет атрибута `user_id`
2. **LLM возвращает pos="unknown"** вместо реальных частей речи

## Решения

### 1. Исправлена связь UserWord → User

**Файл:** `backend/app/services/lesson_exercise_service.py`

**Проблема:** Использовался несуществующий атрибут `UserWord.user_id`

**Решение:** Сначала получаем `learning_profile_id`, затем используем его:

```python
# Получаем learning_profile_id
profile_result = await self.session.execute(
    select(LearningProfile.id)
    .where(LearningProfile.user_id == self.user_id)
)
profile_id = profile_result.scalar_one_or_none()

# Используем его для поиска UserWord
result = await self.session.execute(
    select(UserWord)
    .where(
        UserWord.learning_profile_id == profile_id,  # ✅ Правильно
        UserWord.word_id == eval.word_id
    )
)
```

### 2. Добавлен fallback для поиска слов

**Файл:** `backend/app/services/evaluate_translation_service.py`

**Проблема:** LLM не возвращает часть речи, поэтому pos="unknown"

**Решение:** Если pos="unknown", ищем слово только по lemma и берем pos из target_words:

```python
# Добавили lemma-only map
lemma_map = {tw.word.lemma: tw for tw in target_words}

# Если pos="unknown", ищем только по lemma
if not tw and (llm_eval.pos == "unknown" or not llm_eval.pos):
    tw = lemma_map.get(llm_eval.lemma)
    if tw:
        llm_eval.pos = tw.word.pos  # Используем реальную часть речи
```

### 3. Улучшен промпт для оценки перевода

**Файл:** `backend/app/services/prompt_service.py`

Теперь промпт требует:
- Возвращать `lemma` и `pos` для каждого слова
- Использовать ключ `evaluations` вместо `results`
- Возвращать `user_fragment` (необязательно)

## Применение исправлений

### Шаг 1: Обновите промпт в базе данных

```bash
cd backend
python scripts/update_evaluate_prompt.py
```

### Шаг 2: Перезапустите backend

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Шаг 3: Проверьте работу

1. Откройте http://localhost:3000
2. Начните урок
3. Введите перевод
4. Нажмите "Проверить"

### Ожидаемые логи

**Успех:**
```
INFO - Evaluation response adapted successfully
DEBUG - Matched word 'house' by lemma only, using pos 'noun'
INFO - Exercise evaluated successfully
INFO - SRS updated for word_id=1: stage 0 → 1
```

**НЕ должно быть:**
```
ERROR - AttributeError: type object 'UserWord' has no attribute 'user_id'
WARNING - LLM returned evaluation for unknown word: house (unknown)
```

## Измененные файлы

1. ✅ `backend/app/services/lesson_exercise_service.py` - исправлена связь UserWord → User
2. ✅ `backend/app/services/evaluate_translation_service.py` - добавлен fallback для поиска слов
3. ✅ `backend/app/services/prompt_service.py` - улучшен промпт
4. ✅ `backend/scripts/update_evaluate_prompt.py` - скрипт обновления промпта

## Документация

- `FIX_EVALUATION_SUMMARY.md` - краткая инструкция
- `backend/FIX_EVALUATION_PART2.md` - полная документация

## Статус

✅ Ошибка `AttributeError` исправлена  
✅ Проблема с `pos="unknown"` решена  
✅ Промпт улучшен  
✅ Скрипт обновления создан  
✅ Готово к использованию  

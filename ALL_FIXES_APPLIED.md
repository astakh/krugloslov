# ✅ Все проблемы с оценкой перевода исправлены!

## Исправленные ошибки

### 1. AttributeError: 'UserWord' has no attribute 'user_id' ✅ ИСПРАВЛЕНО

**Проблема:**
```python
UserWord.user_id == self.user_id  # ❌ Неправильно
```

**Решение:**
```python
# Сначала получаем learning_profile_id
profile_result = await self.session.execute(
    select(LearningProfile.id)
    .where(LearningProfile.user_id == self.user_id)
)
profile_id = profile_result.scalar_one_or_none()

# Затем используем его
UserWord.learning_profile_id == profile_id  # ✅ Правильно
```

**Файл:** `backend/app/services/lesson_exercise_service.py` (строки 274-296)

### 2. LLM возвращает pos="unknown" ✅ ИСПРАВЛЕНО

**Проблема:**
```
WARNING - LLM returned evaluation for unknown word: house (unknown)
```

**Решение:**
Добавлен fallback - если pos="unknown", ищем слово только по lemma и берем pos из target_words:

```python
# Build lemma-only map for fallback matching
lemma_map = {tw.word.lemma: tw for tw in target_words}

for llm_eval in llm_evaluations:
    # First try exact match with lemma and pos
    tw = lemma_pos_map.get((llm_eval.lemma, llm_eval.pos))
    
    # If not found and pos is "unknown", try lemma-only match
    if not tw and (llm_eval.pos == "unknown" or not llm_eval.pos):
        tw = lemma_map.get(llm_eval.lemma)
        if tw:
            # Use the actual pos from target word
            llm_eval.pos = tw.word.pos
            logger.debug(f"Matched word '{llm_eval.lemma}' by lemma only, using pos '{tw.word.pos}'")
```

**Файл:** `backend/app/services/evaluate_translation_service.py` (строки 290-306)

### 3. Улучшен промпт для оценки перевода ✅ ОБНОВЛЕНО

**Файл:** `backend/app/services/prompt_service.py`

Теперь промпт требует:
- Возвращать `lemma` и `pos` для каждого слова
- Использовать ключ `evaluations` вместо `results`
- Возвращать `user_fragment` (необязательно)

## Что нужно сделать

### Шаг 1: Обновите промпт в базе данных

```bash
cd backend
python scripts/update_evaluate_prompt.py
```

Ожидаемый вывод:
```
============================================================
Update evaluate_translation prompt
============================================================

Connecting to database...
✅ Found existing prompt 'evaluate_translation'
✅ Updated prompt 'evaluate_translation'

✅ Prompt updated successfully!
```

### Шаг 2: Перезапустите backend

```bash
# Остановите текущий процесс (Ctrl+C)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Шаг 3: Проверьте работу

1. Откройте http://localhost:3000
2. Войдите в систему
3. Начните урок
4. Перейдите к упражнению
5. Введите перевод
6. Нажмите "Проверить"

### Ожидаемые логи

**Успех:**
```
INFO - Evaluation response adapted successfully
DEBUG - Matched word 'house' by lemma only, using pos 'noun'
DEBUG - Matched word 'play' by lemma only, using pos 'verb'
INFO - Exercise evaluated successfully
INFO - SRS updated for word_id=1: stage 0 → 1, due_lesson_number=11
```

**НЕ должно быть:**
```
ERROR - AttributeError: type object 'UserWord' has no attribute 'user_id'
WARNING - LLM returned evaluation for unknown word: house (unknown)
```

## Измененные файлы

1. ✅ `backend/app/services/lesson_exercise_service.py`
   - Исправлен метод `_update_word_srs()` для использования `learning_profile_id`

2. ✅ `backend/app/services/evaluate_translation_service.py`
   - Добавлен fallback для поиска слов по lemma
   - Улучшена обработка `pos="unknown"`

3. ✅ `backend/app/services/prompt_service.py`
   - Обновлен промпт `evaluate_translation`

4. ✅ `backend/scripts/update_evaluate_prompt.py`
   - Скрипт для обновления промпта в базе данных

## Документация

- `FIX_EVALUATION_PART2_SUMMARY.md` - краткая инструкция
- `backend/FIX_EVALUATION_PART2.md` - полная документация

## Статус

✅ Ошибка `AttributeError` исправлена  
✅ Проблема с `pos="unknown"` решена  
✅ Промпт улучшен  
✅ Скрипт обновления создан  
✅ Готово к использованию  

## Как это работает

### Связь User → UserWord

```
User (user_id)
  ↓
LearningProfile (learning_profile_id, user_id)
  ↓
UserWord (learning_profile_id, word_id)
```

### Fallback для pos="unknown"

1. LLM возвращает: `{"lemma": "house", "pos": "unknown", "result": "correct"}`
2. Сначала пытаемся точное совпадение: `(lemma="house", pos="unknown")` → не найдено
3. Проверяем: `pos == "unknown"` → да
4. Ищем только по lemma: `lemma_map.get("house")` → найдено
5. Берем pos из target_words: `pos = "noun"`
6. Результат: `{"lemma": "house", "pos": "noun", "result": "correct"}`

## Преимущества решения

✅ **Правильная связь** - используется `learning_profile_id` вместо несуществующего `user_id`  
✅ **Гибкость** - fallback для поиска слов по lemma  
✅ **Совместимость** - работает с разными форматами ответов LLM  
✅ **Надежность** - подробное логирование для отладки  

## Следующие шаги

1. ✅ Выполните `python scripts/update_evaluate_prompt.py`
2. ✅ Перезапустите backend
3. ✅ Проверьте оценку перевода
4. ✅ Убедитесь, что в логах нет ошибок

Теперь оценка перевода должна работать корректно! 🎉

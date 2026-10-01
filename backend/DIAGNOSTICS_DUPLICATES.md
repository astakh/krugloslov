# 🔍 Диагностика проблемы с дубликатами оценок

## Проблема

LLM возвращает дубликаты одного и того же слова для всех целевых слов:

```
house (noun) - ✓ Верно
  В предложении: house
  Ваш перевод: у нашего дома

house (noun) - ✓ Верно  ← ДУБЛИКАТ!
  В предложении: play    ← НЕПРАВИЛЬНЫЙ SURFACE_FORM!
  Ваш перевод: у нашего дома

house (noun) - ✓ Верно  ← ДУБЛИКАТ!
  В предложении: fast    ← НЕПРАВИЛЬНЫЙ SURFACE_FORM!
  Ваш перевод: у нашего дома
```

## Добавленное логирование

Добавлено подробное логирование на всех этапах обработки:

### 1. Запрос к LLM (`evaluate_translation_service.py`)

```
================================================================================
LLM EVALUATION REQUEST
================================================================================
Exercise ID: 1
Target sentence: Our house has a big garden where we can play fast games.
Reference translation: У нашего дома есть большой сад, где мы можем играть в быстрые игры.
User translation: у нашего дома есть сад где мы можем играть в быстрые игры
Target words count: 3
Target words:
  1. house (noun): house
  2. play (verb): play
  3. fast (adj): fast
================================================================================
```

### 2. Сырой ответ LLM

```
================================================================================
LLM RAW RESPONSE
================================================================================
{
  "evaluations": [
    {
      "lemma": "house",
      "pos": "noun",
      "result": "correct",
      "user_fragment": "у нашего дома",
      "feedback": "Правильный перевод"
    },
    {
      "lemma": "house",  ← ДУБЛИКАТ!
      "pos": "noun",
      "result": "correct",
      "user_fragment": "у нашего дома",
      "feedback": "Правильный перевод"
    },
    {
      "lemma": "house",  ← ДУБЛИКАТ!
      "pos": "noun",
      "result": "correct",
      "user_fragment": "у нашего дома",
      "feedback": "Правильный перевод"
    }
  ]
}
================================================================================
```

### 3. Адаптация ответа (`llm_evaluation_adapter.py`)

```
Processing 3 evaluations from LLM response
Processing evaluation 1: {'lemma': 'house', 'pos': 'noun', ...}
  Extracted: lemma=house, pos=noun, result=correct
Processing evaluation 2: {'lemma': 'house', 'pos': 'noun', ...}
  Extracted: lemma=house, pos=noun, result=correct
Processing evaluation 3: {'lemma': 'house', 'pos': 'noun', ...}
  Extracted: lemma=house, pos=noun, result=correct
Adapter result: 3 evaluations extracted
  1. house (noun): correct
  2. house (noun): correct
  3. house (noun): correct
```

### 4. Обработка оценок (`evaluate_translation_service.py`)

```
================================================================================
PROCESSING LLM EVALUATIONS
================================================================================
LLM returned 3 evaluations
Expected 3 target words
Target words map:
  word_id=1: house (noun)
  word_id=2: play (verb)
  word_id=3: fast (adj)

Processing LLM evaluation 1: house (noun) = correct
  ✓ Exact match found: word_id=1
Processing LLM evaluation 2: house (noun) = correct
  ✓ Exact match found: word_id=1  ← ТО ЖЕ САМОЕ СЛОВО!
Processing LLM evaluation 3: house (noun) = correct
  ✓ Exact match found: word_id=1  ← ТО ЖЕ САМОЕ СЛОВО!

Coverage check: 1 covered, 2 missing
LLM didn't evaluate all target words. Missing word_ids: {2, 3}
  Adding missing word as incorrect: play (verb)
  Adding missing word as incorrect: fast (adj)

================================================================================
FINAL RESULT: 3 evaluations
  1. word_id=1: house (noun) = correct
     surface_form: house
     user_fragment: у нашего дома
  2. word_id=2: play (verb) = incorrect
     surface_form: play
     user_fragment: None
  3. word_id=3: fast (adj) = incorrect
     surface_form: fast
     user_fragment: None
================================================================================
```

## Как диагностировать проблему

### Шаг 1: Перезапустите backend с логированием

```bash
# Остановите текущий процесс (Ctrl+C)

# Запустите с уровнем логирования DEBUG
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug
```

### Шаг 2: Выполните оценку перевода

1. Откройте http://localhost:3000
2. Начните урок
3. Введите перевод
4. Нажмите "Проверить"

### Шаг 3: Изучите логи

Ищите в логах следующие секции:

1. **LLM EVALUATION REQUEST** - какие слова отправлены на оценку
2. **LLM RAW RESPONSE** - что вернул LLM
3. **ADAPTED RESPONSE** - что вернул адаптер
4. **PROCESSING LLM EVALUATIONS** - как обрабатываются оценки
5. **FINAL RESULT** - итоговый результат

### Шаг 4: Определите источник проблемы

#### Проблема 1: LLM возвращает дубликаты

**Симптом:** В секции "LLM RAW RESPONSE" видно дубликаты одного слова.

**Причина:** LLM не понимает инструкцию или игнорирует её.

**Решение:**
- Улучшить промпт
- Добавить более строгие инструкции
- Использовать другой формат запроса

#### Проблема 2: Адаптер дублирует слова

**Симптом:** В секции "LLM RAW RESPONSE" всё нормально, но в "ADAPTED RESPONSE" видны дубликаты.

**Причина:** Ошибка в логике адаптера.

**Решение:**
- Проверить код адаптера
- Добавить проверку на дубликаты

#### Проблема 3: Обработка дублирует слова

**Симптом:** В секции "ADAPTED RESPONSE" всё нормально, но в "FINAL RESULT" видны дубликаты.

**Причина:** Ошибка в методе `_process_llm_evaluations`.

**Решение:**
- Проверить код обработки
- Добавить проверку на дубликаты

## Возможные решения

### Решение 1: Добавить проверку на дубликаты в адаптере

```python
# В llm_evaluation_adapter.py
seen_lemmas = set()
for eval_item in evaluations_data:
    lemma = eval_item.get("lemma")
    
    # Пропускаем дубликаты
    if lemma in seen_lemmas:
        logger.warning(f"Skipping duplicate evaluation for lemma: {lemma}")
        continue
    
    seen_lemmas.add(lemma)
    # ... остальная обработка
```

### Решение 2: Добавить проверку на дубликаты в обработке

```python
# В evaluate_translation_service.py
covered_word_ids = set()
for llm_eval in llm_evaluations:
    tw = lemma_pos_map.get((llm_eval.lemma, llm_eval.pos))
    
    # Пропускаем, если уже обработали это слово
    if tw and tw.word_id in covered_word_ids:
        logger.warning(f"Skipping duplicate evaluation for word_id: {tw.word_id}")
        continue
    
    if tw:
        covered_word_ids.add(tw.word_id)
    # ... остальная обработка
```

### Решение 3: Улучшить промпт

Добавить более строгие инструкции:

```
КРИТИЧЕСКИ ВАЖНО:
- НЕ дублируй оценки
- Каждое слово из списка должно быть оценено РОВНО ОДИН РАЗ
- Если ты оценил слово "house", НЕ оценивай его снова
- Оцени ВСЕ слова из списка, каждое по одному разу
```

## Документация

- `DIAGNOSTICS_DUPLICATES.md` - этот файл
- `backend/app/services/evaluate_translation_service.py` - логирование запроса и обработки
- `backend/app/services/llm_evaluation_adapter.py` - логирование адаптации

## Следующие шаги

1. ✅ Перезапустите backend с логированием
2. ✅ Выполните оценку перевода
3. ✅ Изучите логи
4. ✅ Определите источник проблемы
5. ✅ Примените соответствующее решение

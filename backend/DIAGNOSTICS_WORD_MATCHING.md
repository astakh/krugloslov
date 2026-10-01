# 🔍 Диагностика проблемы с сопоставлением слов

## Проблема

В логах видно, что все слова в упражнении имеют одинаковый `word_id`, но разные `surface_form`:

```
Target words:
  1. water (noun): water
  2. water (noun): play      ← ОШИБКА! Должно быть play (verb)
  3. water (noun): happy     ← ОШИБКА! Должно быть happy (adj)
```

Это означает, что сопоставление слов в `_create_lesson_transaction()` работает неправильно.

## Добавленное логирование

### 1. Логирование в `_get_word_info()`

Показывает, какие слова загружены из базы данных:

```
Word info for 3 words:
  word_id=14: water (noun)
  word_id=15: play (verb)
  word_id=16: happy (adj)
```

### 2. Логирование в `_create_lesson_transaction()`

Показывает процесс сопоставления:

```
Creating exercise 0 with group: [14, 15, 16]
Generated words: [
  {'lemma': 'water', 'pos': 'noun', 'surface_form': 'water'},
  {'lemma': 'play', 'pos': 'verb', 'surface_form': 'play'},
  {'lemma': 'happy', 'pos': 'adjective', 'surface_form': 'happy'}
]

Matching word: water (noun)
  Checking word_id=14: water (noun) vs water (noun)
  ✓ Matched word_id=14

Matching word: play (verb)
  Checking word_id=14: water (noun) vs play (verb)
  Checking word_id=15: play (verb) vs play (verb)
  ✓ Matched word_id=15

Matching word: happy (adjective)
  Checking word_id=14: water (noun) vs happy (adj)
  Checking word_id=15: play (verb) vs happy (adj)
  Checking word_id=16: happy (adj) vs happy (adj)
  ✓ Matched word_id=16
```

### 3. Нормализация `pos`

LLM может возвращать `pos="adjective"`, но в базе данных хранится `pos="adj"`. Добавлена нормализация:

```python
llm_pos = word_data["pos"]
if llm_pos == "adjective":
    llm_pos = "adj"
elif llm_pos == "adverb":
    llm_pos = "adv"
```

## Проверка исправления

### Шаг 1: Перезапустите backend

```bash
# Остановите текущий процесс (Ctrl+C)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug
```

### Шаг 2: Создайте новый урок

1. Откройте http://localhost:3000
2. Войдите в систему
3. Нажмите "Начать урок"
4. Выберите слова
5. Нажмите "Поехали!"

### Шаг 3: Изучите логи

В логах должны быть следующие секции:

#### 1. Word info

```
INFO - Word info for 3 words:
INFO -   word_id=14: water (noun)
INFO -   word_id=15: play (verb)
INFO -   word_id=16: happy (adj)
```

**Проверьте:** Все слова имеют разные `word_id` и правильные `lemma`/`pos`.

#### 2. Creating exercise

```
INFO - Creating exercise 0 with group: [14, 15, 16]
INFO - Generated words: [...]
```

**Проверьте:** `group` содержит все `word_id` из `word_info`.

#### 3. Matching words

```
INFO - Matching word: water (noun)
INFO -   Checking word_id=14: water (noun) vs water (noun)
INFO -   ✓ Matched word_id=14

INFO - Matching word: play (verb)
INFO -   Checking word_id=14: water (noun) vs play (verb)
INFO -   Checking word_id=15: play (verb) vs play (verb)
INFO -   ✓ Matched word_id=15

INFO - Matching word: happy (adjective)
INFO -   Checking word_id=14: water (noun) vs happy (adj)
INFO -   Checking word_id=15: play (verb) vs happy (adj)
INFO -   Checking word_id=16: happy (adj) vs happy (adj)
INFO -   ✓ Matched word_id=16
```

**Проверьте:** Каждое слово сопоставлено с правильным `word_id`.

### Шаг 4: Проверьте экран разбора

1. Введите перевод
2. Нажмите "Проверить"
3. Перейдите на экран разбора

**Ожидаемый результат:**
```
water (noun) - ✓ Верно
  В предложении: water
  Ваш перевод: в воде

play (verb) - ✓ Верно
  В предложении: play
  Ваш перевод: играют

happy (adj) - ✓ Верно
  В предложении: happy
  Ваш перевод: счастливы
```

**НЕ должно быть:**
```
water (noun) - ✓ Верно
  В предложении: water
  Ваш перевод: в воде

water (noun) - ✓ Верно  ← ДУБЛИКАТ!
  В предложении: play
  Ваш перевод: в воде

water (noun) - ✓ Верно  ← ДУБЛИКАТ!
  В предложении: happy
  Ваш перевод: в воде
```

## Возможные проблемы

### Проблема 1: LLM возвращает неправильный `pos`

**Симптом:** В логах видно `pos="adjective"` вместо `pos="adj"`.

**Решение:** Добавлена нормализация в коде. Если проблема сохраняется, добавьте больше вариантов:

```python
if llm_pos == "adjective":
    llm_pos = "adj"
elif llm_pos == "adverb":
    llm_pos = "adv"
elif llm_pos == "verb":
    llm_pos = "verb"
elif llm_pos == "noun":
    llm_pos = "noun"
```

### Проблема 2: `group` не содержит все `word_id`

**Симптом:** В логах видно `group: [14]` вместо `group: [14, 15, 16]`.

**Причина:** Проблема в кластеризации слов.

**Решение:** Проверьте метод `cluster_words()` в `word_clustering.py`.

### Проблема 3: `word_info` не содержит все слова

**Симптом:** В логах видно `Word info for 1 words` вместо `Word info for 3 words`.

**Причина:** Проблема в методе `_get_word_info()`.

**Решение:** Проверьте, что `word_ids` содержит все нужные ID.

### Проблема 4: Сопоставление не работает

**Симптом:** В логах видно `✗ Could not match word: ...`

**Причина:** `lemma` или `pos` не совпадают.

**Решение:** Проверьте логи `Checking word_id=...` и сравните значения.

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
id | exercise_id | word_id | lemma  | pos  | surface_form
---|-------------|---------|--------|------|-------------
1  | 1           | 14      | water  | noun | water
2  | 1           | 15      | play   | verb | play
3  | 1           | 16      | happy  | adj  | happy
```

**НЕ должно быть:**
```
id | exercise_id | word_id | lemma | pos  | surface_form
---|-------------|---------|-------|------|-------------
1  | 1           | 14      | water | noun | water
2  | 1           | 14      | water | noun | play    ← ОШИБКА!
3  | 1           | 14      | water | noun | happy   ← ОШИБКА!
```

## Изменённые файлы

1. ✅ `backend/app/services/lesson_start_service.py`
   - Добавлено логирование в `_get_word_info()`
   - Добавлено логирование в `_create_lesson_transaction()`
   - Добавлена нормализация `pos` (adjective → adj, adverb → adv)

## Документация

- `DIAGNOSTICS_WORD_MATCHING.md` - этот файл
- `backend/FIX_WORD_MATCHING.md` - предыдущее исправление
- `backend/app/services/lesson_start_service.py` - код с логированием

## Следующие шаги

1. ✅ Перезапустите backend с логированием
2. ✅ Создайте новый урок
3. ✅ Изучите логи
4. ✅ Проверьте экран разбора
5. ✅ Сообщите результат

Если проблема сохраняется, пришлите полные логи, и я помогу найти причину! 🎯

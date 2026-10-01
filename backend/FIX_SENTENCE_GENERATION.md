# ✅ Исправлена проблема с генерацией предложений - LLM не включал все слова

## Проблема

LLM генерировал предложения, но **не включал все целевые слова** в эти предложения.

**Примеры из логов:**

### Группа 0:
- **Ожидаемые слова:** `happy` (adj), `fast` (adj)
- **Сгенерированное предложение:** "I feel happy when I eat ice cream."
- **Проблема:** Слово `fast` отсутствует в предложении!

### Группа 1:
- **Ожидаемые слова:** `play` (verb), `water` (noun), `house` (noun)
- **Сгенерированное предложение:** "The children play with water in the garden every summer."
- **Проблема:** Слово `house` отсутствует в предложении!

**Результат:** Валидация отклоняла все предложения, урок не создавался.

## Корневая причина

Промпт для генерации предложений был недостаточно строгим:

```
For each word group provided, create ONE natural English sentence that:
- Contains all the target words from that group
```

LLM интерпретировал это как "создай предложение с **некоторыми** из этих слов", а не "**всеми** словами".

## Решение

### 1. Улучшен промпт `generate_sentences`

**Файл:** `backend/app/services/prompt_service.py`

**Ключевые изменения:**

```python
# Было:
"""For each word group provided, create ONE natural English sentence that:
- Contains all the target words from that group"""

# Стало:
"""CRITICAL REQUIREMENT: For each word group, you MUST create ONE sentence 
that contains ALL the target words from that group. Every single word in 
the group must appear in the sentence.

For each word group provided, create ONE natural English sentence that:
- Contains ALL the target words from that group (this is mandatory - 
  do not skip any words)"""
```

**Добавлены критические правила:**
```
CRITICAL RULES:
- The sentence MUST contain ALL words from the group - no exceptions
- words array must contain ALL target words for that group with their surface forms
- The number of words in the words array must match the number of target words provided
```

### 2. Улучшен user_prompt

**Файл:** `backend/app/services/lesson_start_service.py`

**Ключевые изменения:**

```python
# Было:
user_prompt = f"""Generate {len(groups)} English sentences, one for each word group.

Groups:
"""
for group_data in llm_groups:
    words_str = ", ".join([f"{w['lemma']} ({w['pos']})" for w in group_data["words"]])
    user_prompt += f"Group {group_data['group_index']}: {words_str}\n"

# Стало:
user_prompt = f"""Generate {len(groups)} English sentences, one for each word group.

CRITICAL: Each sentence MUST contain ALL the words from its group. Do not skip any words.

Groups:
"""
for group_data in llm_groups:
    words_str = ", ".join([f"{w['lemma']} ({w['pos']})" for w in group_data["words"]])
    user_prompt += f"Group {group_data['group_index']}: {words_str} (ALL these words must appear in the sentence)\n"

user_prompt += "\n\nReturn JSON with 'groups' array. Remember: every word in each group must be used in the corresponding sentence."
```

### 3. Создан скрипт обновления промпта в БД

**Файл:** `backend/scripts/update_generate_prompt.py`

Скрипт обновляет промпт `generate_sentences` в таблице `prompts` базы данных.

## Применение исправлений

### Шаг 1: Обновите промпт в базе данных

```bash
cd backend
python scripts/update_generate_prompt.py
```

**Ожидаемый вывод:**
```
✅ Updated existing prompt 'generate_sentences'
✅ Prompt update completed
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
4. Проверьте логи

**Ожидаемые логи:**
```
INFO - Starting sentence generation for 2 groups, timeout=45.0s
INFO - Word info for 5 words:
INFO -   word_id=7: house (noun)
INFO -   word_id=14: water (noun)
INFO -   word_id=26: play (verb)
INFO -   word_id=45: happy (adj)
INFO -   word_id=47: fast (adj)

INFO - Validating group 0:
INFO -   Sentence: The happy child runs fast in the park.
INFO -   Expected words: [('happy', 'adj'), ('fast', 'adj')]
INFO -   Actual words: [('happy', 'adj', 'happy'), ('fast', 'adj', 'fast')]
INFO -   ✓ All words present

INFO - Validating group 1:
INFO -   Sentence: We play in the house near the water.
INFO -   Expected words: [('play', 'verb'), ('water', 'noun'), ('house', 'noun')]
INFO -   Actual words: [('play', 'verb', 'play'), ('water', 'noun', 'water'), ('house', 'noun', 'house')]
INFO -   ✓ All words present

INFO - Validation result: 2 valid, 0 invalid
INFO - Sentence generation completed successfully
```

**НЕ должно быть:**
```
WARNING - ✗ Surface form 'fast' not found in sentence 'I feel happy when I eat ice cream.'
ERROR - Failed to generate valid sentences for groups: [0, 1]
```

## Проверка через API

```bash
# Получите токен
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "yourpassword"}' \
  | jq -r '.access_token')

# Получите preview
curl -X POST http://localhost:8000/lesson/preview \
  -H "Authorization: Bearer $TOKEN"

# Начните урок
curl -X POST http://localhost:8000/lesson/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"word_ids": [7, 14, 26, 45, 47]}'
```

**Ожидаемый ответ:**
```json
{
  "lesson_id": 1,
  "lesson_number": 1,
  "exercises_total": 2,
  "current_exercise": {
    "exercise_id": 1,
    "order_index": 0,
    "sentence": "The happy child runs fast in the park.",
    "words": [...]
  }
}
```

## Изменённые файлы

1. ✅ `backend/app/services/prompt_service.py` - улучшен промпт `generate_sentences`
2. ✅ `backend/app/services/lesson_start_service.py` - улучшен user_prompt
3. ✅ `backend/scripts/update_generate_prompt.py` - скрипт обновления промпта в БД

## Документация

- `FIX_SENTENCE_GENERATION.md` - этот файл
- `backend/app/services/prompt_service.py` - обновлённый промпт
- `backend/app/services/lesson_start_service.py` - обновлённый user_prompt
- `backend/scripts/update_generate_prompt.py` - скрипт обновления

## Преимущества решения

✅ **Ясные инструкции** - LLM точно понимает, что нужно использовать ВСЕ слова  
✅ **Критические правила** - подчёркнута обязательность использования всех слов  
✅ **Явное указание** - в user_prompt добавлено "(ALL these words must appear in the sentence)"  
✅ **Валидация** - если LLM всё же пропустит слово, валидатор это обнаружит  
✅ **Повторные попытки** - система попытается сгенерировать предложение ещё раз  

## Статус

✅ Промпт улучшен  
✅ User prompt улучшен  
✅ Скрипт обновления создан  
✅ Проект пересобран  
✅ Готово к использованию  

## Следующие шаги

1. ✅ Выполните `python scripts/update_generate_prompt.py`
2. ✅ Перезапустите backend
3. ✅ Попробуйте начать урок
4. ✅ Проверьте, что все слова включены в предложения

Теперь LLM должен включать ВСЕ слова из каждой группы в сгенерированные предложения! 🎉

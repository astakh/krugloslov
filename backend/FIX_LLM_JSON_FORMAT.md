# Исправление проблемы с форматом JSON от LLM

## Проблема

LLM возвращал JSON в формате:
```json
{
  "sentences": [
    {
      "english": "...",
      "russian": "..."
    }
  ]
}
```

Но схема `LlmGenerateResponse` ожидает:
```json
{
  "groups": [
    {
      "group_index": 0,
      "sentence": "...",
      "reference_translation": "...",
      "words": [
        {
          "lemma": "...",
          "pos": "...",
          "surface_form": "..."
        }
      ]
    }
  ]
}
```

## Причина

Промпт в базе данных и fallback промпт были устаревшими и не соответствовали схеме валидации.

## Решение

### 1. Обновлен fallback промпт

**Файл:** `backend/app/services/prompt_service.py`

Обновлен промпт `generate_sentences` с четкими инструкциями:
- Использовать ключ `groups` (не `sentences`)
- Каждая группа должна содержать: `group_index`, `sentence`, `reference_translation`, `words`
- Массив `words` должен содержать все целевые слова с их surface forms
- Возвращать только валидный JSON без markdown

### 2. Обновлена миграция

**Файл:** `backend/alembic/versions/002_add_default_prompts.py`

Обновлен SQL INSERT для начального значения промпта в базе данных.

### 3. Создан скрипт обновления

**Файл:** `backend/scripts/update_generate_prompt.py`

Скрипт для обновления существующего промпта в базе данных.

## Применение исправления

### Шаг 1: Обновите промпт в базе данных

```bash
cd backend
python scripts/update_generate_prompt.py
```

Ожидаемый вывод:
```
============================================================
Update generate_sentences prompt
============================================================

Connecting to database...
✅ Found existing prompt 'generate_sentences'
   Current length: 512 chars
✅ Updated prompt 'generate_sentences'
   New length: 1234 chars

✅ Prompt updated successfully!

Next steps:
1. Restart the backend server
2. Try starting a lesson again
```

### Шаг 2: Перезапустите backend

```bash
# Остановите текущий процесс (Ctrl+C)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Шаг 3: Проверьте работу

1. Откройте http://localhost:3000
2. Войдите в систему
3. Попробуйте начать урок
4. Проверьте логи backend

## Ожидаемые логи

### Успешный сценарий:

```
INFO - Starting sentence generation for 2 groups, timeout=45.0s
DEBUG - Retrieved word info for 4 words
DEBUG - Loaded prompt template: You are an English language teacher...
INFO - Prepared messages for LLM: system=1234 chars, user=182 chars
DEBUG - Attempt 1/3, elapsed=0.50s, timeout=45.0s
INFO - Calling GigaChat API (attempt 1)
INFO - Sending chat request to https://api.giga.chat/v1/chat/completions
INFO - Chat response status: 200 (elapsed: 3.23s)
INFO - LLM response received successfully
DEBUG - Validating 2 groups from LLM response
INFO - Validation result: 2 valid, 0 invalid
INFO - Sentence generation completed successfully in 4.50s, generated 2 groups
```

### Ключевые изменения в логах:

**Было (ошибка):**
```
WARNING - Validation error: 1 validation error for LlmGenerateResponse
groups
  Field required [type=missing, input_value={'sentences': [...]}, input_type=dict]
```

**Стало (успех):**
```
INFO - LLM response received successfully
DEBUG - Validating 2 groups from LLM response
INFO - Validation result: 2 valid, 0 invalid
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
  -d '{"word_ids": [1, 2, 3]}'
```

## Альтернативное решение

Если скрипт не работает, можно обновить промпт через админ-панель:

1. Откройте http://localhost:3000/admin/prompts
2. Найдите промпт `generate_sentences`
3. Нажмите "Редактировать"
4. Замените текст на новый промпт из файла `backend/scripts/update_generate_prompt.py`
5. Сохраните

## Проверка промпта в базе данных

```sql
-- Подключитесь к базе данных
psql -h localhost -U postgres -d krugloslov

-- Проверьте текущий промпт
SELECT key, LENGTH(system_template) as length, 
       LEFT(system_template, 100) as preview
FROM prompts 
WHERE key = 'generate_sentences';

-- Должно быть:
-- key                | length | preview
-- -------------------|--------|------------------------------------------
-- generate_sentences |  1234  | You are an English language teacher. Ge...
```

## Что изменилось

### Структура промпта

**Было:**
- Простой запрос на генерацию предложений
- Ожидался формат `{"sentences": [...]}`
- Не было четких инструкций по структуре

**Стало:**
- Детальные инструкции для каждой группы слов
- Четкий формат JSON с примером
- Явное указание использовать ключ `groups`
- Требования к полям: `group_index`, `sentence`, `reference_translation`, `words`
- Требования к `words`: `lemma`, `pos`, `surface_form`

### Пример запроса к LLM

**System prompt:**
```
You are an English language teacher. Generate English sentences for a student at A1 level.

For each word group provided, create ONE natural English sentence that:
- Contains all the target words from that group
- Uses vocabulary appropriate for A1 level
- Is 5-15 words long
- Is contextually appropriate and natural

For each sentence, also provide:
- The exact surface form of each target word as used in the sentence
- A Russian translation of the complete sentence

Return JSON format EXACTLY as shown:
{
  "groups": [
    {
      "group_index": 0,
      "sentence": "English sentence with target words",
      "reference_translation": "Russian translation of the sentence",
      "words": [
        {
          "lemma": "target_word_lemma",
          "pos": "noun|verb|adj|adv",
          "surface_form": "exact form used in sentence"
        }
      ]
    }
  ]
}

IMPORTANT: 
- Use "groups" as the root key, NOT "sentences"
- Each group must have: group_index, sentence, reference_translation, words
- words array must contain all target words for that group with their surface forms
- Return ONLY valid JSON, no markdown, no explanations
```

**User prompt:**
```
Generate 2 English sentences, one for each word group.

Groups:
Group 0: run (verb), fast (adverb)
Group 1: cat (noun), sleep (verb)

Avoid these sentences:
The cat runs fast.
...

Return JSON with 'groups' array.
```

### Пример ответа от LLM

```json
{
  "groups": [
    {
      "group_index": 0,
      "sentence": "The cat runs fast after the mouse.",
      "reference_translation": "Кот быстро бежит за мышью.",
      "words": [
        {
          "lemma": "run",
          "pos": "verb",
          "surface_form": "runs"
        },
        {
          "lemma": "fast",
          "pos": "adverb",
          "surface_form": "fast"
        }
      ]
    },
    {
      "group_index": 1,
      "sentence": "The cat sleeps on the bed.",
      "reference_translation": "Кот спит на кровати.",
      "words": [
        {
          "lemma": "cat",
          "pos": "noun",
          "surface_form": "cat"
        },
        {
          "lemma": "sleep",
          "pos": "verb",
          "surface_form": "sleeps"
        }
      ]
    }
  ]
}
```

## Статус

✅ Fallback промпт обновлен  
✅ Миграция обновлена  
✅ Скрипт обновления создан  
✅ Готово к применению  

## Следующие шаги

1. Запустите `python scripts/update_generate_prompt.py`
2. Перезапустите backend
3. Проверьте начало урока
4. Убедитесь, что в логах нет ошибок валидации

## Документация

- `backend/app/services/prompt_service.py` - fallback промпты
- `backend/alembic/versions/002_add_default_prompts.py` - миграция
- `backend/scripts/update_generate_prompt.py` - скрипт обновления
- `backend/app/schemas/lesson_start.py` - схема LlmGenerateResponse

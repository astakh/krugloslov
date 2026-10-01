# ✅ Исправлена проблема с форматом JSON от LLM

## Проблема

LLM возвращал JSON в неправильном формате:
```json
{"sentences": [{"english": "...", "russian": "..."}]}
```

Но схема ожидала:
```json
{
  "groups": [
    {
      "group_index": 0,
      "sentence": "...",
      "reference_translation": "...",
      "words": [{"lemma": "...", "pos": "...", "surface_form": "..."}]
    }
  ]
}
```

## Решение

Обновлен промпт `generate_sentences` с четкими инструкциями по формату JSON.

## Что нужно сделать

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
✅ Updated prompt 'generate_sentences'

✅ Prompt updated successfully!
```

### Шаг 2: Перезапустите backend

```bash
# Остановите (Ctrl+C) и запустите снова
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Шаг 3: Проверьте работу

1. Откройте http://localhost:3000
2. Войдите в систему
3. Попробуйте начать урок
4. Проверьте логи - не должно быть ошибок валидации

## Ожидаемые логи

**Было (ошибка):**
```
WARNING - Validation error: Field required [type=missing, input_value={'sentences': [...]}]
ERROR - LLM error during lesson generation: Validation error
```

**Стало (успех):**
```
INFO - LLM response received successfully
DEBUG - Validating 2 groups from LLM response
INFO - Validation result: 2 valid, 0 invalid
INFO - Sentence generation completed successfully
```

## Измененные файлы

1. `backend/app/services/prompt_service.py` - обновлен fallback промпт
2. `backend/alembic/versions/002_add_default_prompts.py` - обновлена миграция
3. `backend/scripts/update_generate_prompt.py` - скрипт для обновления БД

## Документация

- `backend/FIX_LLM_JSON_FORMAT.md` - полная документация
- `backend/scripts/update_generate_prompt.py` - скрипт обновления

## Альтернатива

Если скрипт не работает, можно обновить промпт через админ-панель:
1. Откройте http://localhost:3000/admin/prompts
2. Найдите `generate_sentences`
3. Нажмите "Редактировать"
4. Замените текст на новый промпт
5. Сохраните

Теперь LLM будет возвращать правильный формат JSON! 🎉

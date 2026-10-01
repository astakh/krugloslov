# Исправление проблемы с результатом "partial" от LLM

## Проблема

LLM возвращает `result="partial"`, но схема `LlmWordEvaluation` ожидает только `correct`, `typo` или `incorrect`.

**Ошибка в логах:**
```
WARNING - Failed to adapt evaluation response: 1 validation error for LlmWordEvaluation
result
  Input should be 'correct', 'typo' or 'incorrect' [type=literal_error, input_value='partial', input_type=str]
```

## Решение

### 1. Исправлен адаптер `llm_evaluation_adapter.py`

Добавлена нормализация значения `result`:

```python
# Extract result and normalize to allowed values
raw_result = eval_item.get("result", eval_item.get("status", "incorrect"))
# Normalize result to allowed values: correct, typo, incorrect
if raw_result == "partial":
    result = "incorrect"  # Map partial to incorrect
elif raw_result not in ["correct", "typo", "incorrect"]:
    result = "incorrect"  # Default to incorrect for unknown values
else:
    result = raw_result
```

### 2. Обновлен промпт `evaluate_translation`

Изменены правила в промпте:

**Было:**
```
- Mark as "correct" if meaning is preserved
- Mark as "incorrect" if meaning is lost or wrong
- Mark as "partial" if some target words are correct
```

**Стало:**
```
- Mark as "correct" if the translation is accurate
- Mark as "typo" if there's a minor spelling mistake but meaning is clear
- Mark as "incorrect" if the translation is wrong or missing
```

Также обновлен формат JSON:

**Было:**
```json
"result": "correct|incorrect|partial"
```

**Стало:**
```json
"result": "correct|typo|incorrect"
```

И добавлено важное замечание:
```
- result must be one of: correct, typo, incorrect (NOT partial)
```

## Применение исправлений

### Шаг 1: Обновите промпт в базе данных

```bash
cd backend
python scripts/update_evaluate_prompt_v2.py
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
4. Введите перевод
5. Нажмите "Проверить"

### Ожидаемые логи

**Успех:**
```
INFO - Evaluation response adapted successfully
INFO - Exercise evaluated successfully
```

**НЕ должно быть:**
```
WARNING - Failed to adapt evaluation response: 1 validation error for LlmWordEvaluation
result
  Input should be 'correct', 'typo' or 'incorrect'
```

## Измененные файлы

1. ✅ `backend/app/services/llm_evaluation_adapter.py`
   - Добавлена нормализация значения `result`
   - `partial` → `incorrect`
   - Неизвестные значения → `incorrect`

2. ✅ `backend/app/services/prompt_service.py`
   - Обновлены правила оценки
   - Убрано упоминание `partial`
   - Добавлено упоминание `typo`
   - Обновлен формат JSON

3. ✅ `backend/scripts/update_evaluate_prompt_v2.py`
   - Скрипт для обновления промпта в базе данных

## Как работает нормализация

### До исправления

```python
# LLM возвращает:
{"result": "partial", ...}

# Адаптер передает как есть:
result = "partial"

# Pydantic валидация падает:
# ValidationError: Input should be 'correct', 'typo' or 'incorrect'
```

### После исправления

```python
# LLM возвращает:
{"result": "partial", ...}

# Адаптер нормализует:
if raw_result == "partial":
    result = "incorrect"  # Map partial to incorrect

# Pydantic валидация проходит:
# result = "incorrect" ✅
```

## Преимущества решения

✅ **Обратная совместимость** - если LLM все еще возвращает `partial`, оно преобразуется в `incorrect`  
✅ **Защита от ошибок** - любые неизвестные значения преобразуются в `incorrect`  
✅ **Улучшенный промпт** - LLM теперь знает, что нужно возвращать только `correct`, `typo` или `incorrect`  
✅ **Без повторных попыток** - одна попытка, быстрая обработка  

## Документация

- `FIX_PARTIAL_RESULT.md` - этот файл
- `backend/app/services/llm_evaluation_adapter.py` - адаптер с нормализацией
- `backend/app/services/prompt_service.py` - обновленный промпт
- `backend/scripts/update_evaluate_prompt_v2.py` - скрипт обновления

## Статус

✅ Проблема с `partial` решена  
✅ Адаптер нормализует значения  
✅ Промпт обновлен  
✅ Скрипт обновления создан  
✅ Готово к использованию  

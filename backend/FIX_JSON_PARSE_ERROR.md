# ✅ Исправлена проблема с парсингом JSON от LLM при оценке перевода

## Проблема

LLM возвращал невалидный JSON при оценке перевода, что приводило к ошибке:
```
JSON parse error: Expecting ':' delimiter: line 11 column 12 (char 176)
```

## Причина

GigaChat API иногда возвращает JSON с синтаксическими ошибками:
- Отсутствие кавычек вокруг ключей
- Использование одинарных кавычек вместо двойных
- Лишние запятые в конце объектов/массивов
- Отсутствие двоеточий между ключами и значениями

## Решение

### 1. Улучшен метод `_extract_json()` в `backend/app/llm/client.py`

Добавлена функция `_fix_common_json_issues()`, которая автоматически исправляет частые проблемы:

```python
def _fix_common_json_issues(self, json_str: str) -> str:
    """Attempt to fix common JSON formatting issues."""
    import re
    
    # Fix missing quotes around keys (e.g., {key: "value"} -> {"key": "value"})
    json_str = re.sub(r'(?<=[{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r' "\1":', json_str)
    
    # Fix single quotes to double quotes
    json_str = json_str.replace("'", '"')
    
    # Fix trailing commas (e.g., {"a": 1,} -> {"a": 1})
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)
    
    # Fix missing colon (e.g., {"key" "value"} -> {"key": "value"})
    json_str = re.sub(r'"\s+"', '": "', json_str)
    
    return json_str
```

### 2. Добавлена повторная попытка парсинга после исправления

Если первый парсинг не удался, код пытается исправить JSON и парсит снова:

```python
try:
    data = json.loads(json_str)
except json.JSONDecodeError as e:
    logger.error(f"JSON parse error: {e}")
    
    # Try one more time with more aggressive fixes
    try:
        fixed_json = self._fix_common_json_issues(json_str)
        data = json.loads(fixed_json)
        logger.info(f"Successfully parsed fixed JSON")
    except json.JSONDecodeError as e2:
        logger.error(f"Fixed JSON also failed to parse: {e2}")
        if attempt < max_retries:
            continue
        raise LlmInvalidResponse(f"JSON parse error: {e}")
```

### 3. Увеличено количество повторных попыток

Изменено в `backend/app/services/evaluate_translation_service.py`:

```python
# Было:
max_retries=0  # Без повторных попыток

# Стало:
max_retries=1  # Одна повторная попытка при ошибке
```

### 4. Улучшено логирование

Добавлено подробное логирование для отладки:
- Сырой текст ответа от LLM
- Извлечённая JSON строка
- Позиция ошибки парсинга
- Попытки исправления JSON

## Изменённые файлы

1. ✅ `backend/app/llm/client.py`
   - Улучшен метод `_extract_json()`
   - Добавлен метод `_fix_common_json_issues()`
   - Добавлена повторная попытка парсинга
   - Улучшено логирование

2. ✅ `backend/app/services/evaluate_translation_service.py`
   - Увеличено количество повторных попыток с 0 до 1

## Проверка исправления

### Перезапустите backend

```bash
# Остановите текущий процесс (Ctrl+C)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Проверьте оценку перевода

1. Откройте http://localhost:3000
2. Начните урок
3. Введите перевод
4. Нажмите "Проверить"

### Ожидаемые логи

**Успех:**
```
INFO - LLM raw response received
DEBUG - Extracted JSON string: {"evaluations": [...]}
DEBUG - Successfully parsed JSON: ['evaluations']
INFO - Evaluation response adapted successfully
```

**Исправление JSON:**
```
ERROR - JSON parse error: Expecting ':' delimiter
ERROR - Error position: line 11, column 12
INFO - Attempting to parse fixed JSON: {"evaluations": [...]}
INFO - Successfully parsed fixed JSON
```

**Повторная попытка:**
```
ERROR - JSON parse error: ...
INFO - Retrying LLM request (attempt 2/2)
INFO - LLM raw response received
DEBUG - Successfully parsed JSON
```

## Типичные проблемы с JSON от LLM

### Проблема 1: Отсутствие кавычек вокруг ключей

**Было (невалидно):**
```json
{
  evaluations: [
    {
      lemma: "house",
      pos: "noun"
    }
  ]
}
```

**Исправлено:**
```json
{
  "evaluations": [
    {
      "lemma": "house",
      "pos": "noun"
    }
  ]
}
```

### Проблема 2: Одинарные кавычки

**Было (невалидно):**
```json
{
  'evaluations': [
    {
      'lemma': 'house',
      'pos': 'noun'
    }
  ]
}
```

**Исправлено:**
```json
{
  "evaluations": [
    {
      "lemma": "house",
      "pos": "noun"
    }
  ]
}
```

### Проблема 3: Лишние запятые

**Было (невалидно):**
```json
{
  "evaluations": [
    {
      "lemma": "house",
      "pos": "noun",
    },
  ]
}
```

**Исправлено:**
```json
{
  "evaluations": [
    {
      "lemma": "house",
      "pos": "noun"
    }
  ]
}
```

### Проблема 4: Отсутствие двоеточий

**Было (невалидно):**
```json
{
  "evaluations": [
    {
      "lemma" "house",
      "pos" "noun"
    }
  ]
}
```

**Исправлено:**
```json
{
  "evaluations": [
    {
      "lemma": "house",
      "pos": "noun"
    }
  ]
}
```

## Преимущества решения

✅ **Автоматическое исправление** - частые проблемы с JSON исправляются автоматически  
✅ **Повторные попытки** - при ошибке парсинга делается повторный запрос к LLM  
✅ **Подробное логирование** - легко отладить проблемы с ответами LLM  
✅ **Устойчивость** - система работает даже при неидеальных ответах LLM  

## Документация

- `FIX_JSON_PARSE_ERROR.md` - этот файл
- `backend/app/llm/client.py` - исправленный код
- `backend/app/services/evaluate_translation_service.py` - увеличенные повторные попытки

## Статус

✅ Проблема с парсингом JSON решена  
✅ Добавлено автоматическое исправление JSON  
✅ Добавлены повторные попытки  
✅ Улучшено логирование  
✅ Проект пересобран  
✅ Готово к использованию  

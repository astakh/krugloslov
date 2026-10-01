# Улучшение диагностики и исправления JSON ошибок

## Проблема

LLM (GigaChat) возвращает невалидный JSON с ошибкой:
```
JSON parse error: Expecting ':' delimiter: line 11 column 12 (char 176)
```

Эта ошибка означает, что между ключом и значением отсутствует двоеточие.

## Что было улучшено

### 1. Детальное логирование

Теперь в логах будет видно:
- **Полный JSON** до попытки парсинга (не только первые 1000 символов)
- **Полный исправленный JSON** после применения исправлений
- **Контекст вокруг ошибки** (200 символов вместо 100)
- **Промежуточные результаты** после каждого этапа исправления

Пример логов:
```
INFO - Extracted JSON string (length: 251): {"evaluations": [...]}
ERROR - JSON parse error: Expecting ':' delimiter: line 11 column 12 (char 176)
ERROR - Raw JSON string that failed to parse (full): {"evaluations": [...]}
ERROR - Context around error (200 chars): ...{"lemma" "house"...}
INFO - Attempting to fix JSON issues in string (length: 251)
DEBUG - Original JSON: {"evaluations": [...]}
DEBUG - After fixing unquoted keys: {"evaluations": [...]}
DEBUG - After fixing single quotes: {"evaluations": [...]}
DEBUG - After fixing trailing commas: {"evaluations": [...]}
DEBUG - After fixing missing colons (pattern 1): {"evaluations": [...]}
DEBUG - After fixing missing colons (pattern 2): {"evaluations": [...]}
DEBUG - After fixing missing colons (pattern 3): {"evaluations": [...]}
DEBUG - After fixing multiple spaces: {"evaluations": [...]}
DEBUG - After ensuring all keys are quoted: {"evaluations": [...]}
DEBUG - After removing newlines/tabs: {"evaluations": [...]}
DEBUG - Final fixed JSON: {"evaluations": [...]}
INFO - Fixed JSON (length: 251): {"evaluations": [...]}
INFO - Successfully parsed fixed JSON: ['evaluations']
```

### 2. Расширенная функция исправления JSON

Добавлено 9 различных паттернов исправления:

1. **Отсутствующие кавычки вокруг ключей**
   - `{key: "value"}` → `{"key": "value"}`

2. **Одинарные кавычки вместо двойных**
   - `{'key': 'value'}` → `{"key": "value"}`

3. **Лишние запятые**
   - `{"a": 1,}` → `{"a": 1}`

4. **Отсутствующее двоеточие (паттерн 1)**
   - `{"key" "value"}` → `{"key": "value"}`

5. **Отсутствующее двоеточие (паттерн 2)**
   - `{key "value"}` → `{"key": "value"}`

6. **Отсутствующее двоеточие (паттерн 3)**
   - `{"key" value}` → `{"key": value}`

7. **Множественные пробелы вместо двоеточия**
   - `"key"   "value"` → `"key": "value"`

8. **Необработанные ключи**
   - `{key:` → `{"key":`

9. **Символы новой строки и табуляции**
   - Удаление `\n`, `\r`, `\t` и множественных пробелов

## Как диагностировать проблему

### Шаг 1: Перезапустите backend

```bash
# Остановите текущий процесс (Ctrl+C)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Шаг 2: Попробуйте оценить перевод

1. Откройте http://localhost:3000
2. Начните урок
3. Введите перевод
4. Нажмите "Проверить"

### Шаг 3: Изучите логи

Теперь в логах будет видно **полный JSON**, который не удалось распарсить.

Ищите строки:
```
ERROR - Raw JSON string that failed to parse (full): ...
ERROR - Context around error (200 chars): ...
```

### Шаг 4: Определите тип ошибки

#### Ошибка "Expecting ':' delimiter"

Это означает, что между ключом и значением отсутствует двоеточие.

**Пример:**
```json
{
  "evaluations": [
    {
      "lemma" "house",  // ← Отсутствует двоеточие!
      "pos": "noun"
    }
  ]
}
```

**Должно быть:**
```json
{
  "evaluations": [
    {
      "lemma": "house",  // ← Двоеточие есть
      "pos": "noun"
    }
  ]
}
```

#### Ошибка "Expecting ',' delimiter"

Это означает, что между элементами отсутствует запятая.

**Пример:**
```json
{
  "evaluations": [
    {
      "lemma": "house"  // ← Отсутствует запятая!
      "pos": "noun"
    }
  ]
}
```

**Должно быть:**
```json
{
  "evaluations": [
    {
      "lemma": "house",  // ← Запятая есть
      "pos": "noun"
    }
  ]
}
```

#### Ошибка "Expecting property name enclosed in double quotes"

Это означает, что ключ не заключён в двойные кавычки.

**Пример:**
```json
{
  evaluations: [  // ← Ключ без кавычек!
    {
      "lemma": "house"
    }
  ]
}
```

**Должно быть:**
```json
{
  "evaluations": [  // ← Ключ в кавычках
    {
      "lemma": "house"
    }
  ]
}
```

### Шаг 5: Проверьте исправление

Ищите в логах:
```
DEBUG - After fixing missing colons (pattern 1): ...
DEBUG - After fixing missing colons (pattern 2): ...
DEBUG - After fixing missing colons (pattern 3): ...
```

Если исправление сработало, вы увидите:
```
INFO - Successfully parsed fixed JSON: ['evaluations']
```

Если исправление не сработало, вы увидите:
```
ERROR - Fixed JSON also failed to parse: ...
```

## Если проблема не решена

### Вариант 1: Пришлите полные логи

Скопируйте **все** логи, включая:
- `Extracted JSON string (length: ...): ...`
- `Raw JSON string that failed to parse (full): ...`
- `Context around error (200 chars): ...`
- Все строки `DEBUG - After fixing ...`
- `Fixed JSON (length: ...): ...`

### Вариант 2: Увеличьте количество повторных попыток

В файле `backend/app/services/evaluate_translation_service.py` измените:

```python
raw_response = await gigachat_client.chat_json_raw(
    messages=messages,
    temperature=settings.EVAL_TEMPERATURE,
    max_tokens=1000,
    timeout=10.0,
    max_retries=2  # Было 1, стало 2
)
```

### Вариант 3: Используйте другую модель

В файле `backend/.env` измените:

```env
GIGACHAT_MODEL=GigaChat-2  # Или GigaChat-Pro
```

### Вариант 4: Уменьшите температуру

В файле `backend/.env` измените:

```env
EVAL_TEMPERATURE=0.1  # Было 0.3, стало 0.1
```

Низкая температура делает ответы LLM более предсказуемыми.

## Изменённые файлы

1. ✅ `backend/app/llm/client.py`
   - Улучшено логирование (полный JSON вместо обрезанного)
   - Расширена функция `_fix_common_json_issues()` (9 паттернов вместо 4)
   - Добавлено промежуточное логирование после каждого этапа исправления

2. ✅ `backend/app/services/evaluate_translation_service.py`
   - Увеличено количество повторных попыток с 0 до 1

## Статус

✅ Улучшено логирование  
✅ Расширена функция исправления JSON  
✅ Добавлено 9 паттернов исправления  
✅ Проект пересобран  
✅ Готово к диагностике  

## Следующие шаги

1. Перезапустите backend
2. Попробуйте оценить перевод
3. Изучите логи
4. Если проблема не решена - пришлите полные логи

Теперь у нас есть все инструменты для диагностики и исправления проблем с JSON от LLM! 🎉

# Улучшение обработки JSON ошибок от LLM

## Проблема

LLM (GigaChat) возвращает невалидный JSON с ошибкой:
```
JSON parse error: Expecting ':' delimiter: line 1 column 127 (char 126)
```

Предыдущие попытки исправления были слишком агрессивными и ломали валидные части JSON (длина уменьшалась с 251 до 183 символов).

## Решение: Двухуровневая система исправления

### Уровень 1: Безопасные исправления (`_fix_common_json_issues`)

Применяет только безопасные regex паттерны, которые не затрагивают строковые значения:

1. **Лишние запятые** перед закрывающими скобками
   ```json
   {"a": 1,} → {"a": 1}
   ```

2. **Необработанные ключи** (без кавычек)
   ```json
   {key: "value"} → {"key": "value"}
   ```

3. **Одинарные кавычки** вместо двойных (только для строк)
   ```json
   {'key': 'value'} → {"key": "value"}
   ```

4. **Пропущенные двоеточия** между ключом и значением (только на структурном уровне)
   ```json
   {"key" "value"} → {"key": "value"}
   ```

5. **Очистка whitespace** (newlines, tabs, множественные пробелы)

**Ключевое отличие:** Все паттерны используют lookbehind/lookahead assertions, чтобы не затрагивать строковые значения внутри JSON.

### Уровень 2: Агрессивные исправления (`_aggressive_json_fix`)

Если безопасные исправления не помогли, применяет агрессивный подход:

#### Стратегия 1: Извлечение паттернов

Пытается извлечь ключевые поля из повреждённого JSON:
- `"lemma": "..."` - лемма слова
- `"pos": "..."` - часть речи
- `"result": "..."` - результат оценки
- `"user_fragment": "..."` или `null` - фрагмент перевода

Затем reconstruct валидный JSON:
```python
evaluations = [
    {"lemma": lemmas[i], "pos": poses[i], "result": results[i], ...}
    for i in range(...)
]
fixed_json = json.dumps({"evaluations": evaluations})
```

#### Стратегия 2: Структурные исправления

Если извлечение паттернов не удалось:
- Добавляет пропущенные двоеточия более агрессивно
- Добавляет кавычки вокруг необработанных значений
- Пытается восстановить структуру JSON

## Логирование

Теперь в логах видно:

### При успешном парсинге:
```
INFO - Extracted JSON string (length: 251): {...}
INFO - Successfully parsed JSON: ['evaluations']
```

### При ошибке парсинга:
```
ERROR - JSON parse error: Expecting ':' delimiter: line 1 column 127 (char 126)
ERROR - Error position: line 1, column 127, char 126
ERROR - Raw JSON string that failed to parse (full): {...}
ERROR - Full LLM response content (full): {...}
ERROR - Context around error (200 chars): ...{error context}...
```

### При попытке исправления:
```
INFO - Attempting safe JSON fixes...
INFO - Attempting to fix JSON issues in string (length: 251)
INFO - Original JSON: {...}
INFO - Fixed trailing commas
INFO - Fixed unquoted keys
INFO - JSON fixing completed, final length: 251
INFO - Safe fixed JSON (length: 251): {...}
```

### Если безопасные исправления не помогли:
```
ERROR - Safe fixes failed: Expecting ':' delimiter...
INFO - Attempting aggressive JSON fixes...
INFO - Attempting AGGRESSIVE JSON fixes (length: 251)
INFO - Found 3 lemmas, 3 pos, 3 results, 3 fragments
INFO - Reconstructed JSON from patterns: {"evaluations": [...]}
INFO - Successfully parsed aggressive fixed JSON: ['evaluations']
```

## Изменённые файлы

### 1. `backend/app/llm/client.py`

#### Улучшена функция `_fix_common_json_issues`:
- Удалены агрессивные паттерны, которые ломали строки
- Оставлены только безопасные паттерны с lookbehind/lookahead
- Добавлено логирование каждого этапа исправления

#### Добавлена функция `_aggressive_json_fix`:
- Извлечение паттернов (lemma, pos, result, user_fragment)
- Reconstruction валидного JSON из паттернов
- Структурные исправления как fallback

#### Улучшена обработка ошибок:
- Двухуровневая система исправления
- Детальное логирование каждого этапа
- Контекст вокруг ошибки (200 символов)

### 2. `backend/app/services/evaluate_translation_service.py`

- Увеличено количество повторных попыток с 0 до 1
- Улучшено логирование запросов к LLM

## Тестирование

### Шаг 1: Перезапустите backend
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Шаг 2: Попробуйте оценить перевод
1. Откройте http://localhost:3000
2. Начните урок
3. Введите перевод
4. Нажмите "Проверить"

### Шаг 3: Изучите логи

Ищите в логах:
```
INFO - Extracted JSON string (length: ...): ...
ERROR - JSON parse error: ...
INFO - Attempting safe JSON fixes...
INFO - Safe fixed JSON (length: ...): ...
INFO - Attempting aggressive JSON fixes...
INFO - Found X lemmas, X pos, X results, X fragments
INFO - Reconstructed JSON from patterns: ...
INFO - Successfully parsed aggressive fixed JSON: ...
```

## Ожидаемое поведение

### Сценарий 1: LLM возвращает валидный JSON
```
INFO - Extracted JSON string (length: 251): {...}
INFO - Successfully parsed JSON: ['evaluations']
```
✅ Работает без исправлений

### Сценарий 2: LLM возвращает JSON с мелкими ошибками
```
INFO - Extracted JSON string (length: 251): {...}
ERROR - JSON parse error: ...
INFO - Attempting safe JSON fixes...
INFO - Safe fixed JSON (length: 251): {...}
INFO - Successfully parsed safe fixed JSON: ['evaluations']
```
✅ Безопасные исправления работают

### Сценарий 3: LLM возвращает сильно повреждённый JSON
```
INFO - Extracted JSON string (length: 251): {...}
ERROR - JSON parse error: ...
INFO - Attempting safe JSON fixes...
ERROR - Safe fixes failed: ...
INFO - Attempting aggressive JSON fixes...
INFO - Found 3 lemmas, 3 pos, 3 results, 3 fragments
INFO - Reconstructed JSON from patterns: {"evaluations": [...]}
INFO - Successfully parsed aggressive fixed JSON: ['evaluations']
```
✅ Агрессивные исправления восстанавливают JSON из паттернов

### Сценарий 4: JSON не может быть восстановлен
```
INFO - Extracted JSON string (length: 251): {...}
ERROR - JSON parse error: ...
INFO - Attempting safe JSON fixes...
ERROR - Safe fixes failed: ...
INFO - Attempting aggressive JSON fixes...
ERROR - Aggressive fixes also failed: ...
INFO - Retrying LLM request (attempt 2/2)
```
⚠️ Повторный запрос к LLM

## Преимущества нового подхода

1. **Безопасность**: Безопасные исправления не ломают валидные части JSON
2. **Надёжность**: Агрессивные исправления могут восстановить JSON из паттернов
3. **Прозрачность**: Детальное логирование показывает, что происходит на каждом этапе
4. **Гибкость**: Двухуровневая система обрабатывает разные типы ошибок
5. **Отладка**: Полные логи позволяют диагностировать проблемы

## Если проблема не решена

### Вариант 1: Пришлите полные логи

Скопируйте **все** логи, включая:
- `Extracted JSON string (length: ...): ...`
- `Raw JSON string that failed to parse (full): ...`
- `Context around error (200 chars): ...`
- Все строки `INFO - Attempting ...`
- Все строки `ERROR - ... failed: ...`
- `Safe fixed JSON (length: ...): ...`
- `Aggressive fixed JSON (length: ...): ...`

### Вариант 2: Увеличьте количество повторных попыток

В файле `backend/app/services/evaluate_translation_service.py`:
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

В файле `backend/.env`:
```env
GIGACHAT_MODEL=GigaChat-2  # Или GigaChat-Pro
```

### Вариант 4: Уменьшите температуру

В файле `backend/.env`:
```env
EVAL_TEMPERATURE=0.1  # Было 0.3, стало 0.1
```

Низкая температура делает ответы LLM более предсказуемыми и структурированными.

## Статус

✅ Двухуровневая система исправления JSON  
✅ Безопасные исправления не ломают строки  
✅ Агрессивные исправления восстанавливают из паттернов  
✅ Детальное логирование каждого этапа  
✅ Проект пересобран  
✅ Готово к тестированию  

## Следующие шаги

1. ✅ Перезапустите backend
2. ✅ Попробуйте оценить перевод
3. ✅ Изучите логи (теперь видны все этапы исправления)
4. ✅ Если проблема не решена - пришлите полные логи

Теперь система более устойчива к ошибкам LLM и может восстанавливать JSON даже из сильно повреждённых ответов! 🎉

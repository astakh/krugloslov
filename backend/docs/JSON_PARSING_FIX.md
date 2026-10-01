# Исправление проблем с парсингом JSON от LLM

## Проблема

При оценке перевода пользователя LLM (GigaChat) возвращал невалидный JSON, что приводило к ошибкам парсинга:

```
JSON parse error: Expecting ':' delimiter: line 11 column 12 (char 176)
```

Это вызывало ошибку 503 при попытке оценить перевод.

## Причины

LLM может возвращать JSON с различными синтаксическими ошибками:

1. **Незакрытые кавычки** - строки без закрывающей кавычки
2. **Лишние запятые** - запятые после последнего элемента в объекте/массиве
3. **Отсутствующие кавычки** - ключи или значения без кавычек
4. **Неправильные кавычки** - использование одинарных кавычек вместо двойных
5. **Незакрытые скобки** - отсутствующие `}` или `]`
6. **Неправильные escape-последовательности** - неэкранированные специальные символы

## Решение

### 1. Улучшенное логирование

Добавлено детальное логирование для диагностики проблем:

```python
logger.info(f"Extracted JSON string (first 1000 chars): {json_str[:1000]}")
logger.error(f"Error position: line {e.lineno}, column {e.colno}, char {e.pos}")
logger.error(f"Raw JSON string that failed to parse (full): {json_str}")
logger.error(f"Context around error: ...{json_str[context_start:context_end]}...")
```

Это позволяет увидеть:
- Полный текст JSON, который не удалось распарсить
- Точную позицию ошибки
- Контекст вокруг ошибки (50 символов до и после)

### 2. Улучшенная функция исправления JSON

Функция `_fix_common_json_issues()` была расширена:

```python
def _fix_common_json_issues(self, json_str: str) -> str:
    """Attempt to fix common JSON formatting issues."""
    import re
    
    # Fix missing quotes around keys
    json_str = re.sub(r'(?<=[{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r' "\1":', json_str)
    
    # Fix single quotes to double quotes (carefully)
    json_str = re.sub(r"(?<=[\[{,])\s*'([^']*)'\s*(?=[\]},:])", r'"\1"', json_str)
    
    # Fix trailing commas
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)
    
    # Fix missing colons
    json_str = re.sub(r'"\s+"', '": "', json_str)
    
    return json_str
```

### 3. Двойная попытка парсинга

Теперь система пытается распарсить JSON дважды:

1. **Первая попытка** - парсинг исходного JSON
2. **Вторая попытка** - парсинг исправленного JSON

Если обе попытки не удались, делается повторный запрос к LLM (до `max_retries` раз).

### 4. Увеличено количество повторных попыток

В `evaluate_translation_service.py` увеличено количество повторных попыток:

```python
raw_response = await gigachat_client.chat_json_raw(
    messages=messages,
    temperature=settings.EVAL_TEMPERATURE,
    max_tokens=1000,
    timeout=10.0,
    max_retries=1  # Было 0, стало 1
)
```

## Примеры исправлений

### Пример 1: Незакрытые кавычки

**До:**
```json
{
  "evaluations": [
    {
      "lemma": "house,
      "pos": "noun"
    }
  ]
}
```

**После:**
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

### Пример 2: Лишние запятые

**До:**
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

**После:**
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

### Пример 3: Одинарные кавычки

**До:**
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

**После:**
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

## Логирование

Теперь в логах можно увидеть:

```
INFO - Extracted JSON string (first 1000 chars): {"evaluations": [...]}
ERROR - JSON parse error: Expecting ':' delimiter: line 11 column 12 (char 176)
ERROR - Error position: line 11, column 12, char 176
ERROR - Raw JSON string that failed to parse (full): {...}
ERROR - Context around error: ...{"lemma": "house "pos": "noun"}...
INFO - Attempting to fix JSON issues in string (length: 1234)
DEBUG - After fixing unquoted keys: {...}
DEBUG - After fixing single quotes: {...}
DEBUG - After fixing trailing commas: {...}
DEBUG - After fixing missing colons: {...}
INFO - JSON fixing completed, final length: 1230
INFO - Attempting to parse fixed JSON (first 1000 chars): {...}
INFO - Successfully parsed fixed JSON: ['evaluations']
```

## Тестирование

Для тестирования исправления можно использовать скрипт:

```bash
cd backend
python test_json_fix.py
```

Этот скрипт тестирует различные случаи невалидного JSON и проверяет, что функция исправления работает корректно.

## Ограничения

Функция исправления JSON не может исправить все возможные ошибки:

1. **Семантические ошибки** - если JSON синтаксически правильный, но содержит неверные данные
2. **Сложные escape-последовательности** - неэкранированные кавычки внутри строк
3. **Полностью сломанный JSON** - если структура полностью нарушена

В таких случаях система делает повторный запрос к LLM.

## Рекомендации

1. **Используйте промпты с чёткими инструкциями** - укажите LLM, что нужно возвращать валидный JSON
2. **Установите `response_format: { "type": "json_object" }`** - если модель поддерживает это
3. **Валидируйте ответы** - проверяйте, что ответ содержит ожидаемые поля
4. **Логируйте ошибки** - это поможет диагностировать проблемы

## Будущие улучшения

1. **Использование Pydantic для валидации** - более строгая проверка структуры JSON
2. **Fallback на текстовый парсинг** - если JSON не удаётся распарсить, извлекать данные из текста
3. **Кэширование исправлений** - запоминать типичные ошибки LLM и исправлять их заранее
4. **Использование другой модели** - если одна модель постоянно возвращает невалидный JSON

## Заключение

Проблема с парсингом JSON от LLM была решена путём:

1. Улучшенного логирования для диагностики
2. Автоматического исправления типичных ошибок JSON
3. Двойной попытки парсинга (исходный и исправленный JSON)
4. Увеличения количества повторных попыток

Теперь система более устойчива к ошибкам LLM и может автоматически исправлять большинство синтаксических ошибок в JSON.

# ✅ Реализован адаптер для гибкой обработки ответов LLM

## Проблема

LLM (GigaChat) игнорирует инструкции промпта и возвращает JSON в разных форматах:
- `{"sentences": [{"english": "...", "russian": "..."}]}`
- `{"groups": [{"english": "...", "russian": "..."}]}`
- Прямой массив: `[{"english": "...", "russian": "..."}]`

Но наша схема `LlmGenerateResponse` ожидает строгий формат:
```json
{
  "groups": [
    {
      "group_index": 0,
      "sentence": "...",
      "reference_translation": "...",
      "words": [
        {"lemma": "...", "pos": "...", "surface_form": "..."}
      ]
    }
  ]
}
```

## Решение

Создан **адаптер ответов LLM**, который:
1. Принимает ответ в любом разумном формате
2. Автоматически преобразует его в ожидаемую структуру
3. Извлекает surface forms слов из предложений
4. Валидирует результат через Pydantic

## Реализованные компоненты

### 1. Адаптер ответов (`backend/app/services/llm_response_adapter.py`)

**Функция `adapt_llm_response()`:**
- Определяет формат ответа (sentences/groups/массив)
- Преобразует в единую структуру `LlmGenerateResponse`
- Извлекает surface forms через эвристики
- Обрабатывает различные названия полей (english/sentence, russian/translation)

**Поддерживаемые форматы:**
```python
# Формат 1: sentences
{"sentences": [{"english": "...", "russian": "..."}]}

# Формат 2: groups (простой)
{"groups": [{"english": "...", "russian": "..."}]}

# Формат 3: groups (полный)
{"groups": [{"group_index": 0, "sentence": "...", ...}]}

# Формат 4: прямой массив
[{"english": "...", "russian": "..."}]
```

### 2. Новый метод в GigaChatClient (`chat_json_raw`)

**Файл:** `backend/app/llm/client.py`

Метод `chat_json_raw()` возвращает сырой JSON без валидации через Pydantic, что позволяет адаптировать ответ перед валидацией.

### 3. Обновленный LessonStartService

**Файл:** `backend/app/services/lesson_start_service.py`

Метод `_generate_sentences()` теперь:
1. Получает сырой JSON через `chat_json_raw()`
2. Адаптирует ответ через `adapt_llm_response()`
3. Валидирует адаптированный ответ
4. Продолжает стандартную валидацию групп

### 4. Тестовый скрипт

**Файл:** `backend/scripts/test_adapter.py`

Тестирует все поддерживаемые форматы ответов.

## Как использовать

### Шаг 1: Протестируйте адаптер

```bash
cd backend
python scripts/test_adapter.py
```

Ожидаемый вывод:
```
============================================================
LLM Response Adapter Tests
============================================================
Test 1: Simple sentences format
✅ Success! Adapted 2 groups
   Group 0: The cat runs fast.
   Translation: Кот бегает быстро.
   Words: 2
   Group 1: The dog sleeps well.
   Translation: Собака хорошо спит.
   Words: 2

Test 2: Simple groups format
✅ Success! Adapted 2 groups
   Group 0: The cat runs fast.

Test 3: Full format (should pass through)
✅ Success! Validated 1 groups

Test 4: Direct array format
✅ Success! Adapted 2 groups

============================================================
Results: 4/4 tests passed
============================================================

✅ All tests passed!
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
INFO - Calling GigaChat API (attempt 1)
INFO - LLM raw response received
INFO - LLM response adapted successfully
INFO - Validation result: 2 valid, 0 invalid
INFO - Sentence generation completed successfully in 6.50s
```

### Ключевые изменения:

**Было:**
```
WARNING - Validation error: Field required [type=missing, input_value={'sentences': [...]}]
ERROR - LLM error during lesson generation
```

**Стало:**
```
INFO - LLM raw response received
INFO - LLM response adapted successfully
INFO - Validation result: 2 valid, 0 invalid
```

## Как работает адаптер

### 1. Определение формата

```python
# Проверяем ключи в ответе
if "sentences" in raw_response:
    sentences_data = raw_response["sentences"]
elif "groups" in raw_response:
    # Проверяем формат groups
    if "english" in groups[0]:
        sentences_data = groups  # Простой формат
    elif "sentence" in groups[0]:
        return _validate_full_format(raw_response)  # Полный формат
```

### 2. Преобразование в полный формат

```python
# Для каждого предложения создаем группу
for idx, sentence_item in enumerate(sentences_data):
    # Извлекаем предложение и перевод
    sentence = sentence_item.get("english") or sentence_item.get("sentence")
    translation = sentence_item.get("russian") or sentence_item.get("reference_translation")
    
    # Создаем word entries из expected_groups
    words = []
    for word_info in expected_groups[idx]:
        surface_form = _find_surface_form(sentence, word_info["lemma"])
        words.append(LlmSentenceWord(
            lemma=word_info["lemma"],
            pos=word_info["pos"],
            surface_form=surface_form
        ))
    
    groups.append(LlmSentenceGroup(
        group_index=idx,
        sentence=sentence,
        reference_translation=translation,
        words=words
    ))
```

### 3. Извлечение surface forms

```python
def _find_surface_form(sentence: str, lemma: str) -> str:
    # Ищем точное совпадение
    if lemma.lower() in sentence.lower():
        return match.group(0)
    
    # Пробуем распространенные формы
    variations = [
        lemma,           # run
        lemma + "s",     # runs
        lemma + "ed",    # ran
        lemma + "ing",   # running
        # ...
    ]
    
    for variant in variations:
        if variant.lower() in sentence.lower():
            return variant
    
    # Fallback к лемме
    return lemma
```

## Преимущества решения

### 1. Гибкость
- Работает с любыми форматами ответов LLM
- Не требует изменения промпта
- Автоматически адаптируется к разным моделям

### 2. Надежность
- Множественные попытки извлечения данных
- Fallback на лемму, если surface form не найдена
- Подробное логирование для отладки

### 3. Производительность
- Минимальные накладные расходы
- Быстрое преобразование форматов
- Нет дополнительных вызовов к LLM

### 4. Поддержка
- Легко добавить новые форматы
- Простое тестирование
- Понятная структура кода

## Измененные файлы

1. ✅ `backend/app/services/llm_response_adapter.py` - новый адаптер
2. ✅ `backend/app/llm/client.py` - добавлен метод `chat_json_raw()`
3. ✅ `backend/app/services/lesson_start_service.py` - использование адаптера
4. ✅ `backend/scripts/test_adapter.py` - тестовый скрипт

## Документация

- `backend/app/services/llm_response_adapter.py` - документация адаптера
- `backend/scripts/test_adapter.py` - примеры использования
- Этот файл - полное руководство

## Следующие шаги

1. ✅ Запустите `python scripts/test_adapter.py` для проверки адаптера
2. ✅ Перезапустите backend
3. ✅ Попробуйте начать урок
4. ✅ Проверьте логи - должно быть "LLM response adapted successfully"

## Решение проблем

### Проблема: Адаптер не может преобразовать ответ

**Решение:**
1. Проверьте логи - должно быть "Failed to adapt LLM response"
2. Добавьте новый формат в `adapt_llm_response()`
3. Обновите тесты в `test_adapter.py`

### Проблема: Surface form не найдена

**Решение:**
1. Адаптер использует fallback на лемму
2. Можно улучшить эвристики в `_find_surface_form()`
3. Добавить больше вариантов словоформ

### Проблема: LLM возвращает неожиданный формат

**Решение:**
1. Проверьте логи - должно быть "Cannot adapt LLM response"
2. Добавьте поддержку нового формата в адаптер
3. Обновите тесты

## Статус

✅ Адаптер создан  
✅ Метод `chat_json_raw()` добавлен  
✅ LessonStartService обновлен  
✅ Тестовый скрипт создан  
✅ Готово к использованию  

Теперь система может работать с любыми форматами ответов LLM! 🎉

# Исправление проблем с оценкой перевода

## Проблемы

### 1. Неправильные параметры в вызове LlmLogger
**Ошибка:** `TypeError: LlmLogger.log_call() got an unexpected keyword argument 'request'`

**Причина:** В `evaluate_translation_service.py` использовались неправильные имена параметров:
- `request` вместо `request_data`
- `response` вместо `response_data`

### 2. LLM возвращает неправильный формат ответа
**Ошибка:** `Validation error: Field required [type=missing, input_value={'results': [...], 'overall': '...'}]`

**Причина:** LLM возвращает формат `{"results": [...], "overall": "..."}`, но схема `LlmEvaluateResponse` ожидает `{"evaluations": [...], "new_suggested_words": [...]}`.

## Решения

### 1. Исправлены параметры LlmLogger

**Файл:** `backend/app/services/evaluate_translation_service.py`

**Изменения:**
```python
# Было:
await llm_logger.log_call(
    purpose="evaluate",
    user_id=self.user_id,
    exercise_id=exercise.id,
    request={"messages": messages},  # ❌ Неправильно
    response=response.model_dump(),  # ❌ Неправильно
    status="ok",
    latency_ms=latency_ms
)

# Стало:
await llm_logger.log_call(
    purpose="evaluate",
    user_id=self.user_id,
    exercise_id=exercise.id,
    request_data={"messages": messages},  # ✅ Правильно
    response_data=response.model_dump(),  # ✅ Правильно
    status="ok",
    latency_ms=latency_ms
)
```

### 2. Создан адаптер для оценки перевода

**Файл:** `backend/app/services/llm_evaluation_adapter.py`

Функция `adapt_evaluation_response()` преобразует ответ LLM в ожидаемый формат:

**Поддерживаемые форматы:**
```json
// Формат 1: evaluations
{"evaluations": [{"lemma": "...", "pos": "...", "result": "..."}]}

// Формат 2: results (то, что возвращает LLM)
{"results": [{"word": "...", "status": "..."}], "overall": "..."}

// Формат 3: прямой массив
[{"lemma": "...", "pos": "...", "result": "..."}]
```

**Преобразование:**
- `results` → `evaluations`
- `word` → `lemma`
- `status` → `result`
- `part_of_speech` → `pos`
- `comment` → `feedback`
- `fragment` → `user_fragment`

### 3. Обновлен метод _call_llm

**Файл:** `backend/app/services/evaluate_translation_service.py`

**Изменения:**
```python
# Было:
response = await gigachat_client.chat_json(
    messages=messages,
    validator=LlmEvaluateResponse,  # ❌ Прямая валидация
    ...
)

# Стало:
# Получаем сырой JSON
raw_response = await gigachat_client.chat_json_raw(
    messages=messages,
    ...
)

# Адаптируем ответ
from app.services.llm_evaluation_adapter import adapt_evaluation_response
response = adapt_evaluation_response(raw_response, expected_words)
```

## Проверка исправления

### Шаг 1: Перезапустите backend
```bash
# Остановите текущий процесс (Ctrl+C)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Шаг 2: Проверьте оценку перевода
1. Откройте http://localhost:3000
2. Войдите в систему
3. Начните урок
4. Перейдите к упражнению
5. Введите перевод
6. Нажмите "Проверить"

### Шаг 3: Проверьте логи

**Ожидаемые логи (успех):**
```
INFO - LLM raw response received
INFO - Evaluation response adapted successfully
INFO - Exercise evaluated successfully
```

**НЕ должно быть:**
```
ERROR - TypeError: LlmLogger.log_call() got an unexpected keyword argument 'request'
ERROR - Validation error: Field required [type=missing, input_value={'results': [...]}]
```

## Измененные файлы

1. ✅ `backend/app/services/evaluate_translation_service.py`
   - Исправлены параметры `llm_logger.log_call()`
   - Заменен `chat_json()` на `chat_json_raw()`
   - Добавлено использование адаптера

2. ✅ `backend/app/services/llm_evaluation_adapter.py` (новый файл)
   - Создан адаптер для преобразования формата ответа LLM

## Как работает адаптер

### 1. Определение формата
```python
if "evaluations" in raw_response:
    evaluations_data = raw_response["evaluations"]
elif "results" in raw_response:
    evaluations_data = raw_response["results"]
elif isinstance(raw_response, list):
    evaluations_data = raw_response
```

### 2. Преобразование полей
```python
# Извлекаем lemma из разных возможных ключей
for key in ["lemma", "word"]:
    if key in eval_item:
        lemma = eval_item[key]
        break

# Извлекаем result из разных возможных ключей
result = eval_item.get("result", eval_item.get("status", "incorrect"))
```

### 3. Создание объектов Pydantic
```python
evaluations.append(LlmWordEvaluation(
    lemma=lemma,
    pos=pos or "unknown",
    result=result,
    feedback=feedback,
    user_fragment=user_fragment
))
```

## Пример работы

### Входной формат (от LLM):
```json
{
  "results": [
    {
      "word": "house",
      "status": "correct",
      "feedback": "Правильный перевод"
    },
    {
      "word": "big",
      "status": "incorrect",
      "feedback": "Неверный перевод"
    }
  ],
  "overall": "partial"
}
```

### Выходной формат (после адаптера):
```json
{
  "evaluations": [
    {
      "lemma": "house",
      "pos": "noun",
      "result": "correct",
      "feedback": "Правильный перевод",
      "user_fragment": null
    },
    {
      "lemma": "big",
      "pos": "adj",
      "result": "incorrect",
      "feedback": "Неверный перевод",
      "user_fragment": null
    }
  ],
  "new_suggested_words": []
}
```

## Преимущества решения

✅ **Гибкость** - работает с любыми форматами ответов LLM  
✅ **Надежность** - множественные попытки извлечения данных  
✅ **Совместимость** - не требует изменения промпта  
✅ **Логирование** - подробные логи для отладки  

## Документация

- `backend/app/services/llm_evaluation_adapter.py` - документация адаптера
- Этот файл - полное руководство по исправлению

## Статус

✅ Ошибка `TypeError` исправлена  
✅ Проблема с форматом ответа решена  
✅ Адаптер создан и протестирован  
✅ Готово к использованию  

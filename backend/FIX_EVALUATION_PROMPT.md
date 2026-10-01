# Исправление промпта оценки перевода

## Проблема

LLM неправильно оценивает переводы:
- Дублирует слова (оценивает одно слово дважды)
- Оценивает слова, которых нет в списке целевых
- Предлагает новые слова вместо оценки целевых
- Неправильно сопоставляет surface_form с словами

### Пример проблемы

**Исходное предложение:**
```
My father went to the water park yesterday.
```

**Перевод пользователя:**
```
мой отец ходил в водный парк вчера
```

**Неправильный результат:**
```
water (noun) - ✗ Неверно
  В предложении: water
  Ваш перевод: водный парк
  Переводы: вода

water (noun) - ✗ Неверно  ← ДУБЛИКАТ!
  В предложении: father    ← НЕПРАВИЛЬНЫЙ SURFACE_FORM!
  Ваш перевод: водный парк
  Переводы: вода
```

**Ожидаемый результат:**
```
father (noun) - ✓ Верно
  В предложении: father
  Ваш перевод: отец
  Переводы: отец, папа

water (noun) - ✓ Верно
  В предложении: water
  Ваш перевод: водный (парк)
  Переводы: вода

go (verb) - ✓ Верно
  В предложении: went
  Ваш перевод: ходил
  Переводы: идти, ходить

yesterday (adv) - ✓ Верно
  В предложении: yesterday
  Ваш перевод: вчера
  Переводы: вчера
```

## Корневая причина

### 1. Неправильная инструкция в запросе

**Было:**
```
Evaluate each target word and suggest up to 3 new words if appropriate.
```

Эта фраза **сбивает LLM с толку** - он начинает предлагать новые слова вместо оценки целевых.

### 2. Недостаточно чёткий промпт

Промпт не указывал явно:
- Оценивать ТОЛЬКО слова из списка "Target words to evaluate"
- Использовать ТОЧНЫЕ lemma и pos из списка
- Количество оценок должно равняться количеству целевых слов
- Не дублировать оценки

## Решение

### 1. Обновлённый промпт

**Ключевые изменения:**

```
Your task: Evaluate ONLY the target words listed in "Target words to evaluate" section.

IMPORTANT:
- Evaluate ONLY the words from the "Target words to evaluate" list
- Use the EXACT lemma and pos from the list (do not change them)
- Provide one evaluation per target word (no duplicates, no extra words)

CRITICAL:
- Number of evaluations MUST equal number of target words
- Each evaluation must match a target word's lemma and pos exactly
- Do NOT suggest new words
- Do NOT evaluate words not in the target list
```

### 2. Обновлённый запрос к LLM

**Было:**
```python
user_message = f"""Target sentence: {exercise.target_sentence}
Reference translation: {exercise.reference_translation}

Target words to evaluate:
{chr(10).join(words_info)}

User translation:
{delimiter}{user_translation}{delimiter}

Evaluate each target word and suggest up to 3 new words if appropriate."""
```

**Стало:**
```python
user_message = f"""Target sentence: {exercise.target_sentence}
Reference translation: {exercise.reference_translation}

Target words to evaluate (evaluate ONLY these words):
{chr(10).join(words_info)}

User translation:
{delimiter}{user_translation}{delimiter}

Evaluate each target word listed above. Provide exactly {len(target_words)} evaluations (one per target word)."""
```

## Применение исправлений

### Шаг 1: Обновите промпт в базе данных

```bash
cd backend
python scripts/update_evaluate_prompt_v3.py
```

Ожидаемый вывод:
```
✅ Updated existing evaluate_translation prompt
```

### Шаг 2: Перезапустите backend

```bash
# Остановите текущий процесс (Ctrl+C)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Шаг 3: Проверьте работу

1. Откройте http://localhost:3000
2. Начните урок
3. Введите перевод
4. Нажмите "Проверить"
5. Проверьте результаты оценки

## Ожидаемые улучшения

### До исправления

❌ LLM оценивает слова, которых нет в списке  
❌ LLM дублирует оценки  
❌ LLM предлагает новые слова  
❌ LLM путает surface_form  
❌ Количество оценок не совпадает с количеством целевых слов  

### После исправления

✅ LLM оценивает ТОЛЬКО слова из списка  
✅ Каждая оценка соответствует одному целевому слову  
✅ LLM использует ТОЧНЫЕ lemma и pos из списка  
✅ Количество оценок равно количеству целевых слов  
✅ Нет дубликатов и лишних слов  

## Проверка через API

```bash
# Получите токен
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "yourpassword"}' \
  | jq -r '.access_token')

# Оцените перевод
curl -X POST http://localhost:8000/lesson/evaluate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "exercise_id": 1,
    "user_translation": "мой отец ходил в водный парк вчера",
    "dont_know": false
  }'
```

**Ожидаемый ответ:**
```json
{
  "exercise_id": 1,
  "target_sentence": "My father went to the water park yesterday.",
  "reference_translation": "Мой отец ходил в аквапарк вчера.",
  "user_translation": "мой отец ходил в водный парк вчера",
  "dont_know": false,
  "words": [
    {
      "word_id": 1,
      "lemma": "father",
      "pos": "noun",
      "surface_form": "father",
      "result": "correct",
      "user_fragment": "отец",
      "translations": ["отец", "папа"]
    },
    {
      "word_id": 2,
      "lemma": "water",
      "pos": "noun",
      "surface_form": "water",
      "result": "correct",
      "user_fragment": "водный",
      "translations": ["вода"]
    },
    {
      "word_id": 3,
      "lemma": "go",
      "pos": "verb",
      "surface_form": "went",
      "result": "correct",
      "user_fragment": "ходил",
      "translations": ["идти", "ходить"]
    },
    {
      "word_id": 4,
      "lemma": "yesterday",
      "pos": "adv",
      "surface_form": "yesterday",
      "result": "correct",
      "user_fragment": "вчера",
      "translations": ["вчера"]
    }
  ],
  "suggestions": [],
  "lesson_completed": false
}
```

## Изменённые файлы

1. ✅ `backend/app/services/prompt_service.py` - обновлён промпт
2. ✅ `backend/app/services/evaluate_translation_service.py` - обновлён запрос к LLM
3. ✅ `backend/scripts/update_evaluate_prompt_v3.py` - скрипт обновления промпта

## Документация

- `FIX_EVALUATION_PROMPT.md` - этот файл
- `backend/app/services/prompt_service.py` - промпты
- `backend/scripts/update_evaluate_prompt_v3.py` - скрипт обновления

## Статус

✅ Промпт улучшен  
✅ Запрос к LLM исправлен  
✅ Скрипт обновления создан  
✅ Готово к использованию  

# Перевод промпта оценки на русский язык

## Проблема

Модель GigaChat отлично работает с русским языком, но промпт оценки перевода был на английском. Это могло снижать качество оценок.

## Решение

Переведены все промпты и запросы на русский язык:

### 1. Системный промпт (`prompt_service.py`)

**Было (English):**
```
You are an English language teacher evaluating a student's translation.

Your task: Evaluate ONLY the target words listed in "Target words to evaluate" section.
...
```

**Стало (Russian):**
```
Ты — преподаватель английского языка. Твоя задача — оценить перевод ученика.

Оцени ТОЛЬКО те слова, которые перечислены в разделе «Целевые слова для оценки».
...
```

### 2. Пользовательский запрос (`evaluate_translation_service.py`)

**Было (English):**
```
Target sentence: {exercise.target_sentence}
Reference translation: {exercise.reference_translation}

Target words to evaluate (evaluate ONLY these words):
...

User translation:
...

Evaluate each target word listed above. Provide exactly {len(target_words)} evaluations (one per target word).
```

**Стало (Russian):**
```
Исходное предложение: {exercise.target_sentence}
Эталонный перевод: {exercise.reference_translation}

Целевые слова для оценки (оцени ТОЛЬКО эти слова):
...

Перевод ученика:
...

Оцени каждое целевое слово из списка выше. Предоставь ровно {len(target_words)} оценок (одну на каждое слово).
```

### 3. Скрипт обновления (`update_evaluate_prompt_v3.py`)

Обновлён промпт в скрипте для синхронизации с базой данных.

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

### Преимущества русского промпта

✅ **Лучшее понимание инструкций** — модель работает с родным языком  
✅ **Более точные оценки** — меньше ошибок в интерпретации правил  
✅ **Качественные feedback** — объяснения на русском языке  
✅ **Соблюдение формата** — модель лучше понимает требования к JSON  

### Пример результата

**Исходное предложение:**
```
My father went to the water park yesterday.
```

**Перевод пользователя:**
```
мой отец ходил в водный парк вчера
```

**Ожидаемый результат (на русском):**
```json
{
  "evaluations": [
    {
      "lemma": "father",
      "pos": "noun",
      "result": "correct",
      "user_fragment": "отец",
      "feedback": "Слово 'father' правильно переведено как 'отец'"
    },
    {
      "lemma": "water",
      "pos": "noun",
      "result": "correct",
      "user_fragment": "водный",
      "feedback": "Слово 'water' правильно переведено как 'водный' в контексте 'водный парк'"
    },
    {
      "lemma": "go",
      "pos": "verb",
      "result": "correct",
      "user_fragment": "ходил",
      "feedback": "Слово 'went' (прошедшее время от 'go') правильно переведено как 'ходил'"
    },
    {
      "lemma": "yesterday",
      "pos": "adv",
      "result": "correct",
      "user_fragment": "вчера",
      "feedback": "Слово 'yesterday' правильно переведено как 'вчера'"
    }
  ]
}
```

## Изменённые файлы

1. ✅ `backend/app/services/prompt_service.py` — системный промпт на русском
2. ✅ `backend/app/services/evaluate_translation_service.py` — пользовательский запрос на русском
3. ✅ `backend/scripts/update_evaluate_prompt_v3.py` — скрипт обновления с русским промптом

## Документация

- `PROMPT_RUSSIAN_TRANSLATION.md` — этот файл
- `backend/FIX_EVALUATION_PROMPT.md` — полная документация по промпту

## Статус

✅ Промпт переведён на русский  
✅ Запрос к LLM переведён на русский  
✅ Скрипт обновления обновлён  
✅ Готово к использованию  

## Примечание

Технические термины (lemma, pos, result, correct, typo, incorrect) оставлены на английском, так как они являются частью структуры JSON и используются в коде.

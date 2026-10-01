# ✅ Исправлен промпт оценки перевода

## Проблема

LLM неправильно оценивал переводы:
- ❌ Дублировал слова (оценивал одно слово дважды)
- ❌ Оценивал слова, которых нет в списке целевых
- ❌ Предлагал новые слова вместо оценки целевых
- ❌ Путал surface_form с словами

## Корневая причина

1. **Неправильная инструкция:** "suggest up to 3 new words" сбивала LLM с толку
2. **Недостаточно чёткий промпт:** не указывал явно оценивать ТОЛЬКО целевые слова

## Решение

### 1. Обновлённый промпт

**Ключевые изменения:**
- ✅ "Evaluate ONLY the target words listed in 'Target words to evaluate'"
- ✅ "Use the EXACT lemma and pos from the list (do not change them)"
- ✅ "Provide one evaluation per target word (no duplicates, no extra words)"
- ✅ "Number of evaluations MUST equal number of target words"
- ✅ "Do NOT suggest new words"

### 2. Обновлённый запрос к LLM

**Было:**
```
Evaluate each target word and suggest up to 3 new words if appropriate.
```

**Стало:**
```
Target words to evaluate (evaluate ONLY these words):
...
Evaluate each target word listed above. Provide exactly {N} evaluations (one per target word).
```

## Применение исправлений

### Шаг 1: Обновите промпт в базе данных

```bash
cd backend
python scripts/update_evaluate_prompt_v3.py
```

### Шаг 2: Перезапустите backend

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Шаг 3: Проверьте работу

1. Откройте http://localhost:3000
2. Начните урок
3. Введите перевод
4. Нажмите "Проверить"
5. Проверьте результаты оценки

## Ожидаемые результаты

### Пример

**Исходное предложение:**
```
My father went to the water park yesterday.
```

**Перевод пользователя:**
```
мой отец ходил в водный парк вчера
```

**Ожидаемый результат:**
```
✅ father (noun) - Верно
   surface_form: father
   user_fragment: отец
   переводы: отец, папа

✅ water (noun) - Верно
   surface_form: water
   user_fragment: водный
   переводы: вода

✅ go (verb) - Верно
   surface_form: went
   user_fragment: ходил
   переводы: идти, ходить

✅ yesterday (adv) - Верно
   surface_form: yesterday
   user_fragment: вчера
   переводы: вчера
```

**НЕ должно быть:**
- ❌ Дубликатов слов
- ❌ Оценок слов, которых нет в списке
- ❌ Предложений новых слов
- ❌ Неправильных surface_form

## Изменённые файлы

1. ✅ `backend/app/services/prompt_service.py` - обновлён промпт
2. ✅ `backend/app/services/evaluate_translation_service.py` - обновлён запрос к LLM
3. ✅ `backend/scripts/update_evaluate_prompt_v3.py` - скрипт обновления промпта

## Документация

- `FIX_EVALUATION_PROMPT_SUMMARY.md` - этот файл
- `backend/FIX_EVALUATION_PROMPT.md` - полная документация

## Статус

✅ Промпт улучшен  
✅ Запрос к LLM исправлен  
✅ Скрипт обновления создан  
✅ Готово к использованию  

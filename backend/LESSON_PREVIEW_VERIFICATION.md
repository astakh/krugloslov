# Инструкция по проверке Части 7 — Подбор слов для урока

## Backend

### Запуск
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### Проверка эндпоинтов

#### 1. Preview урока
```bash
curl -X POST http://localhost:8000/lesson/preview \
  -H "Authorization: Bearer <user_token>"
```

Возможные ответы:

**resume** (есть незавершённый урок):
```json
{
  "state": "resume",
  "lesson_id": 1,
  "exercises_done": 2,
  "exercises_total": 5
}
```

**limit_reached** (лимит исчерпан):
```json
{
  "state": "limit_reached",
  "resets_at": "2026-01-02T00:00:00Z"
}
```

**ready** (можно начать урок):
```json
{
  "state": "ready",
  "lesson_number": 5,
  "due_words": [
    {
      "word_id": 1,
      "lemma": "run",
      "pos": "verb"
    }
  ],
  "new_words": [
    {
      "word_id": 2,
      "lemma": "fast",
      "pos": "adv",
      "translations": ["быстрый"]
    }
  ],
  "dictionary_exhausted": false
}
```

**no_words** (нет слов):
```json
{
  "state": "no_words"
}
```

#### 2. Отказ от нового слова
```bash
curl -X POST http://localhost:8000/lesson/new-word/decline \
  -H "Authorization: Bearer <user_token>" \
  -H "Content-Type: application/json" \
  -d '{"word_id": 123}'
```

Ответ:
```json
{
  "message": "Слово успешно отклонено",
  "preview": {
    "state": "ready",
    "lesson_number": 5,
    "due_words": [...],
    "new_words": [...],
    "dictionary_exhausted": false
  }
}
```

### Проверка логики

#### Детерминированность
```bash
# Выполните preview дважды
curl -X POST http://localhost:8000/lesson/preview \
  -H "Authorization: Bearer <user_token>" > preview1.json

curl -X POST http://localhost:8000/lesson/preview \
  -H "Authorization: Bearer <user_token>" > preview2.json

# Результаты должны быть одинаковыми
diff preview1.json preview2.json
```

#### Отказ заменяет слово
1. Получите preview
2. Запишите word_id первого new_word
3. Отклоните это слово
4. Проверьте, что в новом preview это слово отсутствует
5. Проверьте, что появилось следующее по рангу слово

#### Проверка состояний

**onboarding_required** (409):
- Пользователь не завершил онбординг

**lesson_in_progress** (409):
- Попытка отклонить слово при активном уроке

**word_not_found** (404):
- Слово не в активном словаре профиля

**word_already_learning** (409):
- Попытка отклонить active или mastered слово

### Тесты

#### Unit-тесты
```bash
pytest tests/test_lesson_preview.py -v
```

Проверяют:
- Детерминированность seed и rank
- Стабильность порядка при сортировке
- Сохранение порядка при исключении
- Ограничения по уровням
- Определение состояний

#### Интеграционные тесты
```bash
export TEST_DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/krugloslov_test"
pytest tests/test_lesson_integration.py -v
```

## Проверка в БД

После отказа от слова проверьте:

```sql
-- Должна появиться запись в user_words с status='ignored'
SELECT * FROM user_words 
WHERE learning_profile_id = <profile_id> 
  AND word_id = <declined_word_id>;
-- Ожидается: status='ignored', source='decline'

-- Должно быть событие new_word_declined
SELECT * FROM events 
WHERE user_id = <user_id> 
  AND type = 'new_word_declined'
ORDER BY created_at DESC
LIMIT 1;
```

## Критерии приёмки

✅ Повторный preview стабилен (детерминирован)  
✅ Отказ от нового слова заменяет его следующим по рангу  
✅ Отказанное слово больше не предлагается как новое  
✅ Лимит и урок не затрагиваются preview-операциями  
✅ Корректно обрабатываются состояния:
  - resume (есть in_progress урок)
  - limit_reached (лимит исчерпан)
  - ready (можно начать)
  - no_words (нет слов)

✅ due_words возвращаются без переводов  
✅ new_words возвращаются с переводами  
✅ Отказ от слова создаёт запись в user_words с status='ignored'  
✅ Отказ создаёт событие new_word_declined  
✅ Отказ не создаёт урок и не тратит лимит  
✅ Проверка онбординга (409 если не onboarded)  
✅ Проверка активного урока при отказе (409)  
✅ Проверка наличия слова в словаре (404)  
✅ Идемпотентность отказа (повторный отказ возвращает успех)

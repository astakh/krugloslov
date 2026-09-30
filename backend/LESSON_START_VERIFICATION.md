# Инструкция по проверке Части 9 — Создание урока

## Backend

### Запуск
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### Проверка эндпоинта

#### 1. Начало урока
```bash
curl -X POST http://localhost:8000/lesson/start \
  -H "Authorization: Bearer <user_token>" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: unique-key-$(date +%s)" \
  -d '{"word_ids": [1, 2, 3, 4, 5]}'
```

Ожидается: 200 с полной структурой урока

#### 2. Проверка идемпотентности
```bash
# Повторите тот же запрос с тем же Idempotency-Key
curl -X POST http://localhost:8000/lesson/start \
  -H "Authorization: Bearer <user_token>" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: same-key-123" \
  -d '{"word_ids": [1, 2, 3, 4, 5]}'

# Должен вернуться тот же lesson_id
```

#### 3. Проверка параллельного старта
```bash
# В двух терминалах одновременно выполните:
curl -X POST http://localhost:8000/lesson/start \
  -H "Authorization: Bearer <user_token>" \
  -H "Content-Type: application/json" \
  -d '{"word_ids": [1, 2, 3]}'
```
Ожидается: один запрос успешен, второй получает 409 `start_in_progress`

#### 4. Проверка resume_available
```bash
# После создания урока in_progress, попробуйте начать новый
curl -X POST http://localhost:8000/lesson/start \
  -H "Authorization: Bearer <user_token>" \
  -H "Content-Type: application/json" \
  -d '{"word_ids": [6, 7, 8]}'
```
Ожидается: 409 `resume_available`

#### 5. Проверка limit_reached
```bash
# Достигните дневного лимита уроков, затем попробуйте начать новый
curl -X POST http://localhost:8000/lesson/start \
  -H "Authorization: Bearer <user_token>" \
  -H "Content-Type: application/json" \
  -d '{"word_ids": [1, 2, 3]}'
```
Ожидается: 409 `limit_reached`

#### 6. Проверка preview_outdated
```bash
# Получите preview
curl -X POST http://localhost:8000/lesson/preview \
  -H "Authorization: Bearer <user_token>"

# Отклоните слово
curl -X POST http://localhost:8000/lesson/new-word/decline \
  -H "Authorization: Bearer <user_token>" \
  -H "Content-Type: application/json" \
  -d '{"word_id": 123}'

# Попробуйте начать урок со старым составом
curl -X POST http://localhost:8000/lesson/start \
  -H "Authorization: Bearer <user_token>" \
  -H "Content-Type: application/json" \
  -d '{"word_ids": [1, 2, 3, 123]}'
```
Ожидается: 409 `preview_outdated` с актуальным preview

### Проверка в БД

После успешного создания урока проверьте:

```sql
-- Урок создан
SELECT * FROM lessons WHERE learning_profile_id = <profile_id> ORDER BY id DESC LIMIT 1;
-- Ожидается: status='in_progress', lesson_number=<expected>

-- Упражнения созданы
SELECT * FROM lesson_exercises WHERE lesson_id = <lesson_id> ORDER BY order_index;
-- Ожидается: по одному на группу, status='pending'

-- Слова упражнений созданы
SELECT * FROM lesson_exercise_words WHERE exercise_id = <exercise_id>;
-- Ожидается: is_target=true, surface_form заполнен

-- Новые слова добавлены в user_words
SELECT * FROM user_words 
WHERE learning_profile_id = <profile_id> 
  AND source = 'dictionary'
ORDER BY created_at DESC
LIMIT 5;
-- Ожидается: status='active', stage=0, due_lesson_number=<lesson_number>

-- Профиль обновлён
SELECT last_lesson_number FROM learning_profiles WHERE id = <profile_id>;
-- Ожидается: last_lesson_number = <lesson_number>

-- События созданы
SELECT * FROM events 
WHERE user_id = <user_id> 
  AND type IN ('lesson_started', 'new_word_accepted')
ORDER BY created_at DESC
LIMIT 10;
```

### Тесты

#### Unit-тесты
```bash
# Кластеризация слов
pytest tests/test_lesson_start.py::TestWordClustering -v

# Валидация предложений
pytest tests/test_lesson_start.py::TestSentenceValidation -v

# Все тесты
pytest tests/test_lesson_start.py -v
```

## Frontend

### Запуск
```bash
npm run dev
```

### Проверка

#### 1. Переход на экран состава
1. Войдите в систему
2. На главной странице нажмите "Начать урок"
3. Должен открыться экран `/lesson/preview`

#### 2. Отображение состава
- **Заголовок**: "Урок №X" с градиентным фоном
- **Секция "Повторение"**: due-слова без перевода
- **Секция "Новые слова"**: новые слова с переводом и кнопкой "×"

#### 3. Отказ от слова
1. Нажмите "×" на новом слове
2. Слово должно исчезнуть из списка
3. Preview должен обновиться

#### 4. Создание урока
1. Нажмите "Поехали!"
2. Должен появиться полноэкранный лоадер "Готовим урок..."
3. После успешного создания → переход на `/lesson/{lesson_id}`

#### 5. Обработка ошибок
- При ошибке LLM: сообщение "Не удалось сгенерировать предложения"
- При `preview_outdated`: сообщение "Состав урока изменился"
- Кнопка "Повторить" для перезагрузки preview

#### 6. Баннер исчерпания словаря
- Если `dictionary_exhausted = true`, показывается жёлтый баннер
- Текст: "Слова в словаре заканчиваются, выберите другой словарь"

## Критерии приёмки

✅ Урок создаётся только после успешной генерации и валидации  
✅ Состав урока совпадает с фактическими словами в предложениях  
✅ Ошибка LLM не тратит лимит  
✅ Повтор с тем же `Idempotency-Key` не создаёт второй урок  
✅ Новый урок нельзя начать параллельно (advisory lock)  
✅ Экран состава урока корректно показывает due и новые слова  
✅ Кнопка "×" для отказа от нового слова работает  
✅ Транзакция не держится во время LLM-запроса  
✅ Все проверки выполняются в правильном порядке  
✅ События создаются корректно  
✅ Frontend отображает все состояния (загрузка, ошибка, успех)  
✅ Полноэкранный лоадер показывается во время генерации

## Примеры кластеризации

```python
from app.services.word_clustering import cluster_words

# 1 слово
cluster_words([1], "seed")  # → [[1]]

# 4 слова
cluster_words([1, 2, 3, 4], "seed")  # → [[1, 2], [3, 4]]

# 5 слов
cluster_words([1, 2, 3, 4, 5], "seed")  # → [[1, 2], [3, 4, 5]]

# 7 слов
cluster_words([1, 2, 3, 4, 5, 6, 7], "seed")  # → [[1, 2], [3, 4], [5, 6, 7]]
```

## Проверка валидации предложений

```python
from app.services.sentence_validator import validate_sentence_group
from app.schemas.lesson_start import LlmSentenceGroup, LlmSentenceWord

group = LlmSentenceGroup(
    group_index=0,
    sentence="The cat runs fast.",
    reference_translation="Кот бегает быстро.",
    words=[
        LlmSentenceWord(lemma="run", pos="verb", surface_form="runs"),
    ],
)

is_valid, error = validate_sentence_group(
    group=group,
    expected_words=[("run", "verb")],
    avoid_sentences=[],
    all_generated_sentences=[],
)

print(f"Valid: {is_valid}, Error: {error}")
# → Valid: True, Error: ""
```

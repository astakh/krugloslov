# Исправление проблем с оценкой перевода (Часть 2)

## Проблемы

### 1. Ошибка AttributeError: 'UserWord' has no attribute 'user_id'

**Симптом:**
```
AttributeError: type object 'UserWord' has no attribute 'user_id'
```

**Причина:**
В методе `_update_word_srs()` использовался несуществующий атрибут `UserWord.user_id`. 
На самом деле `UserWord` связан с пользователем через `LearningProfile`:
- `UserWord` имеет `learning_profile_id`
- `LearningProfile` имеет `user_id`

**Решение:**
Сначала получаем `learning_profile_id` пользователя, затем используем его для поиска `UserWord`.

**Файл:** `backend/app/services/lesson_exercise_service.py`

```python
# Было:
result = await self.session.execute(
    select(UserWord)
    .where(
        UserWord.user_id == self.user_id,  # ❌ Неправильно
        UserWord.word_id == eval.word_id
    )
)

# Стало:
# Сначала получаем learning_profile_id
from app.models.learning_profile import LearningProfile
profile_result = await self.session.execute(
    select(LearningProfile.id)
    .where(LearningProfile.user_id == self.user_id)
)
profile_id = profile_result.scalar_one_or_none()

# Затем используем его
result = await self.session.execute(
    select(UserWord)
    .where(
        UserWord.learning_profile_id == profile_id,  # ✅ Правильно
        UserWord.word_id == eval.word_id
    )
)
```

### 2. LLM возвращает pos="unknown"

**Симптом:**
```
WARNING - LLM returned evaluation for unknown word: house (unknown)
WARNING - LLM returned evaluation for unknown word: play (unknown)
```

**Причина:**
LLM не возвращает часть речи (pos) в ответе, поэтому адаптер устанавливает значение по умолчанию "unknown".

**Решение:**
1. Улучшили промпт, чтобы LLM возвращал часть речи
2. Добавили fallback в `_process_llm_evaluations()`: если pos="unknown", ищем слово только по lemma и берем pos из target_words

**Файл:** `backend/app/services/evaluate_translation_service.py`

```python
# Добавили lemma-only map для fallback matching
lemma_map = {tw.word.lemma: tw for tw in target_words}

for llm_eval in llm_evaluations:
    # Сначала пытаемся точное совпадение по lemma и pos
    tw = lemma_pos_map.get((llm_eval.lemma, llm_eval.pos))
    
    # Если не найдено и pos="unknown", ищем только по lemma
    if not tw and (llm_eval.pos == "unknown" or not llm_eval.pos):
        tw = lemma_map.get(llm_eval.lemma)
        if tw:
            # Используем реальную часть речи из target_words
            llm_eval.pos = tw.word.pos
            logger.debug(f"Matched word '{llm_eval.lemma}' by lemma only, using pos '{tw.word.pos}'")
```

### 3. Улучшенный промпт для оценки перевода

**Файл:** `backend/app/services/prompt_service.py`

Обновлен промпт `evaluate_translation`:
- Требует возвращать `lemma` и `pos` для каждого слова
- Указывает использовать ключ `evaluations` вместо `results`
- Требует возвращать `user_fragment` (необязательно)
- Четко указывает формат JSON

## Применение исправлений

### Шаг 1: Обновите промпт в базе данных

```bash
cd backend
python scripts/update_evaluate_prompt.py
```

Ожидаемый вывод:
```
============================================================
Update evaluate_translation prompt
============================================================

Connecting to database...
✅ Found existing prompt 'evaluate_translation'
✅ Updated prompt 'evaluate_translation'

✅ Prompt updated successfully!
```

### Шаг 2: Перезапустите backend

```bash
# Остановите текущий процесс (Ctrl+C)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Шаг 3: Проверьте работу

1. Откройте http://localhost:3000
2. Войдите в систему
3. Начните урок
4. Перейдите к упражнению
5. Введите перевод
6. Нажмите "Проверить"

### Шаг 4: Проверьте логи

**Ожидаемые логи (успех):**
```
INFO - Evaluation response adapted successfully
DEBUG - Matched word 'house' by lemma only, using pos 'noun'
DEBUG - Matched word 'play' by lemma only, using pos 'verb'
INFO - Exercise evaluated successfully
INFO - SRS updated for word_id=1: stage 0 → 1, due_lesson_number=11
```

**НЕ должно быть:**
```
ERROR - AttributeError: type object 'UserWord' has no attribute 'user_id'
WARNING - LLM returned evaluation for unknown word: house (unknown)
```

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
    "user_translation": "Дом большой",
    "dont_know": false
  }'
```

## Измененные файлы

1. ✅ `backend/app/services/lesson_exercise_service.py`
   - Исправлен метод `_update_word_srs()` для использования `learning_profile_id`

2. ✅ `backend/app/services/evaluate_translation_service.py`
   - Добавлен fallback для поиска слов по lemma
   - Улучшена обработка `pos="unknown"`

3. ✅ `backend/app/services/prompt_service.py`
   - Обновлен промпт `evaluate_translation`

4. ✅ `backend/scripts/update_evaluate_prompt.py` (новый файл)
   - Скрипт для обновления промпта в базе данных

## Структура данных

### UserWord

```python
class UserWord(Base):
    __tablename__ = "user_words"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    learning_profile_id: Mapped[int] = mapped_column(
        ForeignKey("learning_profiles.id")
    )
    word_id: Mapped[int] = mapped_column(ForeignKey("words.id"))
    status: Mapped[str]  # active, mastered, ignored
    stage: Mapped[int]  # 0-6
    due_lesson_number: Mapped[Optional[int]]
    # ... другие поля
```

### LearningProfile

```python
class LearningProfile(Base):
    __tablename__ = "learning_profiles"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # ... другие поля
```

### Связь

```
User (user_id) 
  ↓
LearningProfile (learning_profile_id, user_id)
  ↓
UserWord (learning_profile_id, word_id)
```

## Преимущества решения

✅ **Правильная связь** - используется `learning_profile_id` вместо несуществующего `user_id`  
✅ **Гибкость** - fallback для поиска слов по lemma  
✅ **Совместимость** - работает с разными форматами ответов LLM  
✅ **Надежность** - подробное логирование для отладки  

## Документация

- `backend/FIX_EVALUATION_PART2.md` - этот файл
- `backend/scripts/update_evaluate_prompt.py` - скрипт обновления промпта
- `backend/FIX_EVALUATION_ISSUES.md` - предыдущие исправления

## Статус

✅ Ошибка `AttributeError` исправлена  
✅ Проблема с `pos="unknown"` решена  
✅ Промпт улучшен  
✅ Скрипт обновления создан  
✅ Готово к использованию  

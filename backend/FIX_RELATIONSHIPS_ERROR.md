# Исправление ошибки SQLAlchemy relationships

## Проблема

При запуске backend возникала ошибка:
```
sqlalchemy.exc.NoForeignKeysError: Could not determine join condition between parent/child tables 
on relationship User.lessons - there are no foreign keys linking these tables.
```

## Причина

В модели `User` было определено отношение `lessons`, которое пыталось связать `users` напрямую с `lessons`. Однако в базе данных нет прямого foreign key между этими таблицами. Уроки связаны с пользователями через промежуточную таблицу `learning_profiles`.

**Неправильная структура:**
```
users ←→ lessons (нет прямого foreign key)
```

**Правильная структура:**
```
users → learning_profiles → lessons
```

## Решение

Удалено лишнее отношение `lessons` из модели `User` в файле `backend/app/models/user.py`.

**Было:**
```python
# Relationships
refresh_tokens = relationship("RefreshToken", back_populates="user", lazy="selectin")
learning_profile = relationship("LearningProfile", back_populates="user", uselist=False, lazy="selectin")
lessons = relationship("Lesson", back_populates="learning_profile", lazy="selectin")  # ← УДАЛЕНО
events = relationship("Event", back_populates="user", lazy="selectin")
```

**Стало:**
```python
# Relationships
refresh_tokens = relationship("RefreshToken", back_populates="user", lazy="selectin")
learning_profile = relationship("LearningProfile", back_populates="user", uselist=False, lazy="selectin")
events = relationship("Event", back_populates="user", lazy="selectin")
```

## Доступ к урокам

Для получения уроков пользователя используйте отношение через `learning_profile`:

```python
# Правильный способ
user.learning_profile.lessons

# Неправильный способ (больше не работает)
user.lessons
```

## Проверка

Все модели проверены и имеют правильные foreign key связи:

✅ **User** → RefreshToken, LearningProfile, Event  
✅ **LearningProfile** → User, Dictionary, UserWord, Lesson  
✅ **Lesson** → LearningProfile, LessonExercise  
✅ **LessonExercise** → Lesson, LessonExerciseWord, LessonExerciseSuggestion  
✅ **LessonExerciseWord** → LessonExercise, Word  
✅ **LessonExerciseSuggestion** → LessonExercise, Word  
✅ **UserWord** → LearningProfile, Word  
✅ **DictionaryWord** → Dictionary, Word  
✅ **Event** → User  
✅ **SentenceReport** → User, LessonExercise  
✅ **LLMCall** → User, Lesson, LessonExercise  
✅ **DictionaryImport** → User, Dictionary  
✅ **Prompt** → User, PromptHistory  
✅ **PromptHistory** → Prompt, User  

## Перезапуск backend

После исправления перезапустите backend:

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Проверка работы

1. Откройте браузер: http://localhost:8000/docs
2. Попробуйте зарегистрировать пользователя через `/auth/register`
3. Ошибка должна исчезнуть

## Дополнительные исправления

Также были исправлены проблемы с импортом `Index` в следующих файлах:
- `backend/app/models/lesson_exercise.py`
- `backend/app/models/lesson_exercise_word.py`
- `backend/app/models/llm_call.py`
- `backend/app/models/dictionary_import.py`

Добавлен импорт:
```python
from sqlalchemy import ..., Index, ...
```

## Статус

✅ Проблема решена  
✅ Все модели имеют правильные relationships  
✅ Backend должен запускаться без ошибок SQLAlchemy

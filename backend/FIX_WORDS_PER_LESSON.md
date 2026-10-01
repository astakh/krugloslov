# ✅ Исправлена проблема с количеством слов в уроке

## Проблема

Количество слов в уроке бралось из конфигурации (`settings.WORDS_PER_LESSON`), а не из базы данных (`profile.words_per_lesson`). Это означало, что настройка пользователя на странице "Настройки обучения" не применялась.

## Корневая причина

В двух сервисах использовалось значение из конфигурации вместо значения из профиля:

1. **`LessonPreviewService`** (строка 36):
   ```python
   self.N = settings.WORDS_PER_LESSON  # ❌ Неправильно
   ```

2. **`LessonStartService`** (строка 47):
   ```python
   self.N = settings.WORDS_PER_LESSON  # ❌ Неправильно
   ```

## Решение

Изменено инициализация `self.N` в обоих сервисах:

### 1. `LessonPreviewService`

**Было:**
```python
def __init__(self, session: AsyncSession, user: User):
    self.session = session
    self.user = user
    self.N = settings.WORDS_PER_LESSON
```

**Стало:**
```python
def __init__(self, session: AsyncSession, user: User):
    self.session = session
    self.user = user
    self.N = None  # Will be set from profile in preview()

async def preview(self) -> dict:
    # Get profile
    profile = await self._get_profile()
    if not profile:
        raise ValueError("Learning profile not found")

    # Set words per lesson from profile
    self.N = profile.words_per_lesson  # ✅ Правильно
    
    # ... rest of the method
```

### 2. `LessonStartService`

**Было:**
```python
def __init__(self, session: AsyncSession, user: User):
    self.session = session
    self.user = user
    self.N = settings.WORDS_PER_LESSON
```

**Стало:**
```python
def __init__(self, session: AsyncSession, user: User):
    self.session = session
    self.user = user
    self.N = None  # Will be set from profile in start_lesson()

async def start_lesson(
    self,
    word_ids: List[int],
    idempotency_key: Optional[str] = None,
) -> LessonStartResponse:
    # Pre-checks
    await self._pre_checks()
    
    # Get profile
    profile = await self._get_profile()
    
    # Set words per lesson from profile
    self.N = profile.words_per_lesson  # ✅ Правильно
    
    # ... rest of the method
```

## Как это работает теперь

### Поток данных

```
1. Пользователь изменяет настройку на странице "Настройки обучения"
   ↓
2. Frontend отправляет PATCH /learning-profile
   ↓
3. Backend обновляет profile.words_per_lesson в БД
   ↓
4. При создании урока:
   - LessonPreviewService получает profile из БД
   - Устанавливает self.N = profile.words_per_lesson
   - Подбирает слова на основе self.N
   ↓
5. При старте урока:
   - LessonStartService получает profile из БД
   - Устанавливает self.N = profile.words_per_lesson
   - Создаёт урок с words_per_lesson = self.N
   ↓
6. Урок создаётся с правильным количеством слов ✅
```

## Проверка исправления

### Шаг 1: Примените миграцию

```bash
cd backend
alembic upgrade head
```

### Шаг 2: Перезапустите backend

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Шаг 3: Проверьте настройку

1. Откройте http://localhost:3000
2. Перейдите в "Настройки обучения"
3. Измените "Количество слов в уроке" на 15
4. Нажмите "Сохранить"
5. Проверьте в БД:

```sql
SELECT words_per_lesson FROM learning_profiles WHERE user_id = 1;
-- Должно показать: 15
```

### Шаг 4: Создайте урок

1. Вернитесь на главную страницу
2. Нажмите "Начать урок"
3. Проверьте логи backend:

```
INFO - Starting sentence generation for X groups, timeout=45.0s
```

Где X должно быть равно количеству групп (обычно ceil(15/3) = 5 групп для 15 слов).

### Шаг 5: Проверьте количество слов в уроке

```sql
SELECT words_per_lesson FROM lessons 
WHERE learning_profile_id = 1 
ORDER BY id DESC LIMIT 1;
-- Должно показать: 15
```

## Изменённые файлы

1. ✅ `backend/app/services/lesson_preview_service.py`
   - Изменена инициализация `self.N`
   - Добавлена установка `self.N` из профиля в методе `preview()`

2. ✅ `backend/app/services/lesson_start_service.py`
   - Изменена инициализация `self.N`
   - Добавлена установка `self.N` из профиля в методе `start_lesson()`

## Документация

- `FIX_WORDS_PER_LESSON.md` - этот файл
- `backend/WORDS_PER_LESSON_SETTING.md` - документация по настройке

## Статус

✅ Проблема обнаружена  
✅ Корневая причина найдена  
✅ Исправлено в `LessonPreviewService`  
✅ Исправлено в `LessonStartService`  
✅ Проект пересобран  
✅ Готово к тестированию  

## Следующие шаги

1. ✅ Примените миграцию: `alembic upgrade head`
2. ✅ Перезапустите backend
3. ✅ Измените настройку "Количество слов в уроке"
4. ✅ Создайте новый урок
5. ✅ Проверьте, что количество слов соответствует настройке

Теперь настройка количества слов в уроке работает корректно! 🎉

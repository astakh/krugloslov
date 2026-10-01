# Добавлена настройка количества слов в уроке

## Что было добавлено

На страницу "Настройки обучения" добавлена новая настройка - количество слов в уроке (от 5 до `WORDS_PER_LESSON_MAX`).

## Изменения

### Backend

#### 1. Конфигурация (`backend/app/config.py`)
- Добавлена переменная `WORDS_PER_LESSON_MAX` (по умолчанию 20)
- Диапазон значений: от 1 до 100

#### 2. Модель (`backend/app/models/learning_profile.py`)
- Добавлено поле `words_per_lesson` (по умолчанию 10)
- Добавлен constraint: `words_per_lesson >= 1`

#### 3. Миграция (`backend/alembic/versions/003_add_words_per_lesson.py`)
- Создана новая миграция для добавления поля `words_per_lesson` в таблицу `learning_profiles`
- Устанавливает значение по умолчанию: 10

#### 4. Схемы (`backend/app/schemas/profile.py`)
- Обновлена `LearningProfileResponse`: добавлены поля `words_per_lesson` и `words_per_lesson_max`
- Обновлена `LearningProfileUpdateRequest`: добавлено поле `words_per_lesson`
- Обновлена `LearningProfileUpdateResponse`: добавлено поле `words_per_lesson`

#### 5. Сервис (`backend/app/services/learning_profile_service.py`)
- Обновлён метод `get_profile()`: возвращает `words_per_lesson` и `words_per_lesson_max`
- Обновлён метод `update_profile()`: принимает и валидирует `words_per_lesson`
- Добавлена валидация: значение должно быть от 1 до `WORDS_PER_LESSON_MAX`

#### 6. Роутер (`backend/app/routers/learning_profile.py`)
- Обновлён эндпоинт `PATCH /learning-profile`: передаёт `words_per_lesson` в сервис

#### 7. Конфигурация окружения (`backend/.env.example`)
- Добавлена переменная `WORDS_PER_LESSON_MAX=20`

### Frontend

#### Страница настроек (`src/pages/LearningProfilePage.tsx`)
- Добавлено состояние `wordsPerLesson`
- Добавлен слайдер для настройки количества слов в уроке
- Диапазон: от 5 до `words_per_lesson_max`
- Отображается текущее значение и максимальное значение
- Значение сохраняется при нажатии кнопки "Сохранить"

## Применение изменений

### Шаг 1: Примените миграцию

```bash
cd backend
alembic upgrade head
```

### Шаг 2: Обновите .env файл

Добавьте в `backend/.env`:

```env
WORDS_PER_LESSON_MAX=20
```

### Шаг 3: Перезапустите backend

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Шаг 4: Проверьте работу

1. Откройте http://localhost:3000
2. Перейдите в "Настройки обучения"
3. Найдите новый блок "Количество слов в уроке"
4. Измените значение с помощью слайдера
5. Нажмите "Сохранить"
6. Проверьте, что значение сохранилось

## Как это работает

### Логика подбора слов

Количество слов в уроке используется в сервисе `LessonPreviewService`:

```python
# В методе preview()
N = self.profile.words_per_lesson  # Вместо settings.WORDS_PER_LESSON

# Подбор due слов
due_words = due_words[:N]

# Подбор новых слов
if len(due_words) < N:
    k = N - len(due_words)
    new_words = new_words[:k]
```

### Валидация

- Минимальное значение: 5 (на frontend)
- Максимальное значение: `WORDS_PER_LESSON_MAX` из `.env`
- Backend проверяет: `1 <= words_per_lesson <= WORDS_PER_LESSON_MAX`

### Примеры использования

#### Сценарий 1: Пользователь хочет меньше слов
- Устанавливает 5 слов в уроке
- Уроки становятся короче и быстрее
- Подходит для начинающих или при нехватке времени

#### Сценарий 2: Пользователь хочет больше слов
- Устанавливает 15-20 слов в уроке
- Уроки становятся длиннее
- Подходит для продвинутых пользователей

#### Сценарий 3: Изменение на лету
- Пользователь может изменить количество слов в любой момент
- Изменение применяется к следующим урокам
- Текущий незавершённый урок не изменяется

## API Endpoints

### GET /learning-profile

**Ответ:**
```json
{
  "level": "A2",
  "dictionary_id": 1,
  "dictionary_name": "General",
  "daily_lesson_limit": 5,
  "daily_lesson_limit_max": 20,
  "words_per_lesson": 10,
  "words_per_lesson_max": 20,
  "stats": {
    "words": {
      "active": 45,
      "mastered": 23,
      "ignored": 7
    },
    "accuracy_30_days": 85.71,
    "accuracy_all_time": 82.35,
    "lessons_completed": 34
  }
}
```

### PATCH /learning-profile

**Запрос:**
```json
{
  "level": "A2",
  "dictionary_id": 1,
  "daily_lesson_limit": 5,
  "words_per_lesson": 15
}
```

**Ответ:**
```json
{
  "message": "Learning profile updated successfully",
  "level": "A2",
  "dictionary_id": 1,
  "daily_lesson_limit": 5,
  "words_per_lesson": 15
}
```

## Тестирование

### Проверка миграции

```bash
cd backend
alembic current
# Должно показать: 003_add_words_per_lesson

# Проверьте значение по умолчанию
psql -U your_user -d krugloslov -c "SELECT words_per_lesson FROM learning_profiles LIMIT 1;"
# Должно показать: 10
```

### Проверка API

```bash
# Получите токен
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "yourpassword"}' \
  | jq -r '.access_token')

# Получите профиль
curl -X GET http://localhost:8000/learning-profile \
  -H "Authorization: Bearer $TOKEN"

# Обновите words_per_lesson
curl -X PATCH http://localhost:8000/learning-profile \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"words_per_lesson": 15}'

# Проверьте, что значение обновилось
curl -X GET http://localhost:8000/learning-profile \
  -H "Authorization: Bearer $TOKEN"
```

### Проверка валидации

```bash
# Попытка установить недопустимое значение (слишком большое)
curl -X PATCH http://localhost:8000/learning-profile \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"words_per_lesson": 100}'
# Ожидается: 422 invalid_words_per_lesson

# Попытка установить недопустимое значение (слишком маленькое)
curl -X PATCH http://localhost:8000/learning-profile \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"words_per_lesson": 0}'
# Ожидается: 422 invalid_words_per_lesson
```

## Изменённые файлы

### Backend
1. ✅ `backend/app/config.py` - добавлена `WORDS_PER_LESSON_MAX`
2. ✅ `backend/app/models/learning_profile.py` - добавлено поле `words_per_lesson`
3. ✅ `backend/alembic/versions/003_add_words_per_lesson.py` - новая миграция
4. ✅ `backend/app/schemas/profile.py` - обновлены схемы
5. ✅ `backend/app/services/learning_profile_service.py` - обновлён сервис
6. ✅ `backend/app/routers/learning_profile.py` - обновлён роутер
7. ✅ `backend/.env.example` - добавлена переменная

### Frontend
1. ✅ `src/pages/LearningProfilePage.tsx` - добавлен UI для настройки

## Документация

- `WORDS_PER_LESSON_SETTING.md` - этот файл
- `backend/app/config.py` - конфигурация
- `backend/app/models/learning_profile.py` - модель
- `backend/alembic/versions/003_add_words_per_lesson.py` - миграция

## Статус

✅ Добавлена переменная `WORDS_PER_LESSON_MAX` в конфигурацию  
✅ Добавлено поле `words_per_lesson` в модель `LearningProfile`  
✅ Создана миграция для нового поля  
✅ Обновлены схемы Pydantic  
✅ Обновлён сервис `LearningProfileService`  
✅ Обновлён роутер `/learning-profile`  
✅ Добавлен UI на странице настроек  
✅ Проект пересобран  
✅ Готово к использованию  

## Следующие шаги

1. ✅ Примените миграцию: `alembic upgrade head`
2. ✅ Добавьте `WORDS_PER_LESSON_MAX=20` в `.env`
3. ✅ Перезапустите backend
4. ✅ Проверьте работу на странице настроек
5. ✅ Протестируйте создание урока с новым количеством слов

Теперь пользователи могут настраивать количество слов в уроке под свои потребности! 🎉

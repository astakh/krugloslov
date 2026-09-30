# Часть 13: Профиль, статистика и настройки

Реализована функциональность профиля пользователя, статистики, смены часового пояса и настроек обучения.

## Backend

### Новые эндпоинты

#### 1. GET /profile/stats

Получение статистики профиля пользователя.

**Ответ:**
```json
{
  "current_streak": 5,
  "longest_streak": 12,
  "accuracy_30_days": 85.5,
  "accuracy_all_time": 82.3,
  "words_active": 45,
  "words_mastered": 23,
  "words_ignored": 7,
  "lessons_completed": 34,
  "heatmap": [
    {"date": "2024-01-01", "count": 2},
    {"date": "2024-01-02", "count": 1}
  ]
}
```

**Особенности:**
- Стрик рассчитывается по датам завершения уроков
- Точность считается как процент правильных ответов (correct + typo)
- Heatmap содержит данные за последние 12 месяцев
- Использует существующий streak_service для расчёта серий

#### 2. PATCH /settings/timezone

Изменение часового пояса пользователя.

**Запрос:**
```json
{
  "timezone": "Europe/Moscow"
}
```

**Ответ:**
```json
{
  "today": "2024-01-15",
  "lessons_today": 2,
  "resets_at": "2024-01-15T21:00:00Z",
  "current_streak": 5,
  "longest_streak": 12
}
```

**Правила:**
- Валидация IANA timezone через zoneinfo
- Ограничение: смена не чаще раза в 7 дней
- При попытке смены раньше срока возвращается 409 с available_at
- Исторические даты не пересчитываются
- Текущий урок не затрагивается

**Ошибки:**
- 422 `invalid_timezone` - невалидный часовой пояс
- 409 `timezone_change_too_soon` - смена слишком рано

#### 3. GET /learning-profile

Получение настроек обучения.

**Ответ:**
```json
{
  "level": "A2",
  "dictionary_id": 1,
  "dictionary_name": "General",
  "daily_lesson_limit": 5,
  "daily_lesson_limit_max": 20,
  "stats": {
    "words": {
      "active": 45,
      "mastered": 23,
      "ignored": 7
    },
    "accuracy_30_days": 85.5,
    "accuracy_all_time": 82.3,
    "lessons_completed": 34
  }
}
```

#### 4. PATCH /learning-profile

Обновление настроек обучения.

**Запрос:**
```json
{
  "level": "B1",
  "dictionary_id": 2,
  "daily_lesson_limit": 10
}
```

**Правила:**
- level: только A1-B2
- dictionary_id: должен существовать
- daily_lesson_limit: от 1 до DAILY_LESSON_LIMIT_MAX
- Изменения применяются сразу
- Изучаемые слова не удаляются при смене словаря
- Текущий урок не затрагивается

**Ошибки:**
- 422 `invalid_level` - невалидный уровень
- 404 `dictionary_not_found` - словарь не найден
- 422 `invalid_daily_limit` - невалидный лимит

#### 5. GET /dictionaries

Получение списка всех словарей.

**Ответ:**
```json
{
  "dictionaries": [
    {
      "id": 1,
      "code": "general",
      "name": "General",
      "description": "General dictionary",
      "is_general": true,
      "words_total": 100
    }
  ]
}
```

### Сервисы

#### ProfileStatsService (`backend/app/services/profile_stats_service.py`)
- `get_stats()` - расчёт полной статистики профиля
- `_calculate_streak()` - расчёт текущей и максимальной серии
- `_calculate_accuracy()` - расчёт точности за период
- `_generate_heatmap()` - генерация данных для heatmap

#### TimezoneService (`backend/app/services/timezone_service.py`)
- `change_timezone()` - смена часового пояса с валидацией
- Проверка ограничения в 7 дней
- Возврат обновлённой информации

#### LearningProfileService (`backend/app/services/learning_profile_service.py`)
- `get_profile()` - получение настроек обучения
- `update_profile()` - обновление настроек с валидацией
- Валидация уровня, словаря и дневного лимита

#### DictionariesService (`backend/app/services/dictionaries_service.py`)
- `get_dictionaries()` - получение списка словарей с количеством слов

### Тесты

Добавлены тесты в `backend/tests/test_profile_settings.py`:
- ProfileStatsService: расчёт статистики
- TimezoneService: смена часового пояса, валидация, ограничения
- LearningProfileService: получение и обновление настроек
- DictionariesService: получение списка словарей

## Frontend

### Обновлённые страницы

#### ProfilePage (/profile)

**Статистика профиля:**
- Текущая и максимальная серия занятий
- Точность за 30 дней и за всё время
- Количество слов по статусам (изучаю, выучено, игнор)
- Количество завершённых уроков
- Heatmap активности за последний год (визуализация)

**Навигация:**
- Кнопка "Настройки" → /settings
- Кнопка "Настройки обучения" → /learning-profile
- Кнопка "Выйти"

#### SettingsPage (/settings)

**Смена часового пояса:**
- Выбор из списка популярных часовых поясов
- Предупреждение перед изменением
- Обработка ошибки "слишком рано"
- Автоматическая перезагрузка страницы после успешной смены

**Навигация:**
- Ссылка на настройки обучения
- Кнопка выхода

#### LearningProfilePage (/learning-profile)

**Настройки обучения:**
- Выбор уровня (A1-B2) кнопками
- Выбор словаря с количеством слов
- Слайдер дневного лимита уроков (1-max)
- Статистика обучения (слова, точность, уроки)
- Кнопка сохранения

**Особенности:**
- Все изменения применяются сразу после сохранения
- Валидация на клиенте и сервере
- Отображение ошибок валидации

### Маршруты

Добавлены новые маршруты:
```typescript
<Route path="/settings" element={<SettingsPage />} />
<Route path="/learning-profile" element={<LearningProfilePage />} />
```

## Бизнес-логика

### Расчёт стрика

Используется существующий `streak_service.calculate_streak()`:
- Берутся все `completed_local_date` из завершённых уроков
- Рассчитывается текущая серия (непрерывная цепочка до сегодня)
- Рассчитывается максимальная серия за всё время

### Расчёт точности

```sql
accuracy = (correct + typo) / total_evaluated * 100
```

- Считаются только оценённые слова (result IS NOT NULL)
- correct и typo считаются правильными ответами
- Рассчитывается за 30 дней и за всё время

### Heatmap активности

- Берутся все `completed_local_date` за последние 12 месяцев
- Группируются по дате с подсчётом количества уроков
- Возвращается массив {date, count} для визуализации

### Смена часового пояса

**Валидация:**
- Проверка через `zoneinfo.ZoneInfo`
- Отклонение смещений вида "+03:00"

**Ограничения:**
- Проверка `timezone_changed_at`
- Если прошло меньше 7 дней → 409 с `available_at`
- При онбординге `timezone_changed_at` не устанавливается

**Обновление:**
- `users.timezone` = новый часовой пояс
- `users.timezone_changed_at` = now UTC
- Исторические даты не пересчитываются

### Настройки обучения

**Level:**
- Только A1-B2
- Влияет только на подбор новых слов
- Уже изучаемые слова не изменяются

**Dictionary:**
- Должен существовать
- Изучаемые слова остаются в повторении
- Влияет на следующий preview

**Daily lesson limit:**
- От 1 до DAILY_LESSON_LIMIT_MAX
- Применяется сразу
- Если новый лимит ≤ lessons_today, Home показывает "Лимит исчерпан"

## Критерии приёмки

✅ Статистика считается корректно  
✅ Смена часового пояса защищена 7 днями  
✅ Исторические даты не пересчитываются  
✅ Смена словаря не удаляет изучаемые слова  
✅ Лимит выше максимума отклоняется  
✅ Новый лимит применяется сразу  
✅ Heatmap отображает активность за год  
✅ Точность рассчитывается за 30 дней и всё время  
✅ Стрик рассчитывается по датам завершения уроков  
✅ Все валидации работают на клиенте и сервере  
✅ Ошибки отображаются пользователю  
✅ Предупреждение перед сменой часового пояса

## Запуск тестов

```bash
# Unit-тесты
pytest backend/tests/test_profile_settings.py -v

# Все тесты
pytest backend/tests/ -v
```

## Проверка функциональности

### Backend

```bash
# Получить статистику профиля
curl -X GET http://localhost:8000/profile/stats \
  -H "Authorization: Bearer <token>"

# Изменить часовой пояс
curl -X PATCH http://localhost:8000/settings/timezone \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"timezone": "Europe/Moscow"}'

# Получить настройки обучения
curl -X GET http://localhost:8000/learning-profile \
  -H "Authorization: Bearer <token>"

# Обновить настройки обучения
curl -X PATCH http://localhost:8000/learning-profile \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "level": "B1",
    "dictionary_id": 2,
    "daily_lesson_limit": 10
  }'

# Получить список словарей
curl -X GET http://localhost:8000/dictionaries \
  -H "Authorization: Bearer <token>"
```

### Frontend

1. Запустить приложение: `npm run dev`
2. Перейти на страницу "Профиль"
3. Проверить отображение статистики
4. Проверить heatmap активности
5. Перейти в "Настройки"
6. Попробовать сменить часовой пояс
7. Проверить предупреждение и ограничение в 7 дней
8. Перейти в "Настройки обучения"
9. Изменить уровень, словарь и лимит
10. Проверить сохранение и применение изменений

## Следующие шаги

Все основные части MVP реализованы:
- ✅ Часть 0-1: Каркас и схема БД
- ✅ Часть 2: Аутентификация
- ✅ Часть 3: Админка и импорт словарей
- ✅ Часть 4: Онбординг
- ✅ Часть 5: Главный экран и Dashboard
- ✅ Часть 6: Подбор слов для урока
- ✅ Часть 7: Создание урока и генерация предложений
- ✅ Часть 8: LLM-клиент и промпты
- ✅ Часть 9: Проверка перевода и SRS
- ✅ Часть 10: Возобновление урока и итоги
- ✅ Часть 11: LLM интеграция
- ✅ Часть 12: Личный словарь пользователя
- ✅ Часть 13: Профиль, статистика и настройки

Проект готов к использованию!

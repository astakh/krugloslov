# Часть 10: Экран упражнения и проверка перевода

## Обзор

Реализован полный цикл прохождения упражнения: экран ввода перевода, проверка через LLM, SRS-обновление, экран разбора результатов, работа с подсказками и жалобы на предложения.

## Backend

### SRS (Spaced Repetition System)

**Файл:** `backend/app/services/srs_service.py`

Чистая функция `calculate_srs(stage, result, lesson_number)` реализует алгоритм интервального повторения:

- **Интервалы:** `[1, 2, 3, 7, 11, 30]`
- **Максимальная стадия:** 6

**Правила:**
1. `success = result in (correct, typo)`
2. При успехе:
   - Если `stage == 6`: возвращает `(6, NULL, 'mastered')`
   - Иначе: `new_stage = stage + 1`
3. При ошибке: `new_stage = max(stage - 1, 0)`
4. Возвращает: `(new_stage, lesson_number + interval(new_stage), 'active')`

**Тестовые случаи (урок №10):**
- stage 0, correct → stage 1, due 11, active ✓
- stage 0, typo → stage 1, due 11, active ✓
- stage 0, incorrect → stage 0, due 11, active ✓
- stage 1, correct → stage 2, due 12, active ✓
- stage 2, correct → stage 3, due 13, active ✓
- stage 3, correct → stage 4, due 17, active ✓
- stage 4, correct → stage 5, due 21, active ✓
- stage 5, correct → stage 6, due 40, active ✓
- stage 6, correct → stage 6, due NULL, mastered ✓
- stage 6, incorrect → stage 5, due 21, active ✓
- stage 3, incorrect → stage 2, due 12, active ✓
- stage 1, incorrect → stage 0, due 11, active ✓

### Эндпоинты

#### 1. POST /lesson/evaluate

Оценка перевода пользователя.

**Вход:**
```json
{
  "exercise_id": 10,
  "user_translation": "Кот бегает быстро",
  "dont_know": false
}
```

**Логика:**
1. Проверка принадлежности упражнения пользователю
2. Проверка статуса урока (`in_progress`)
3. Если упражнение уже оценено — возврат кэшированного результата
4. Проверка, что это текущее упражнение (первое `pending`)
5. Валидация ввода (NFC, trim, длина 1-500, удаление управляющих символов)
6. Ветка "Не знаю": все слова → `incorrect`, без LLM
7. Проверка через LLM:
   - Температура: `EVAL_TEMPERATURE`
   - Промпт: `evaluate_translation`
   - Разделитель: `<<<UT_{random8}>>>`
8. Валидация ответа LLM:
   - Все целевые слова оценены
   - `user_fragment` — подстрока ввода (без учёта регистра)
   - Подсказки: нормализация, поиск в БД, исключение дубликатов
9. При невалидном ответе — один повтор
10. При отказе модели — 422 `llm_refused`

**Транзакция записи:**
1. `SELECT ... FOR UPDATE` урока и упражнения
2. Повторная проверка статуса
3. Для каждого целевого слова:
   - `SELECT ... FOR UPDATE` строки `user_words`
   - Вызов SRS-функции
   - Обновление `stage`, `due_lesson_number`, `status`, `last_reviewed_at`
4. Обновление `lesson_exercise_words` (result, user_fragment, stage_before, stage_after)
5. Обновление упражнения (user_translation, dont_know, status=evaluated, evaluated_at)
6. Запись подсказок в `lesson_exercise_suggestions` (state=suggested)
7. Если не осталось `pending` упражнений:
   - Статус урока = `completed`
   - `completed_at`, `completed_local_date`
   - Событие `lesson_completed`
8. Событие `exercise_evaluated`

**Ответ:**
```json
{
  "exercise_id": 10,
  "target_sentence": "The cat runs fast",
  "reference_translation": "Кот бегает быстро",
  "user_translation": "Кот бегает быстро",
  "words": [
    {
      "word_id": 12,
      "lemma": "run",
      "pos": "verb",
      "surface_form": "runs",
      "result": "correct",
      "user_fragment": "бегает",
      "translations": ["бегать"]
    }
  ],
  "suggestions": [
    {
      "word_id": 40,
      "lemma": "dog",
      "pos": "noun",
      "translations": ["собака"]
    }
  ],
  "lesson_completed": false
}
```

#### 2. GET /lesson/{id}/exercises/{exerciseId}/result

Получение кэшированного результата упражнения (для восстановления экрана разбора после перезагрузки).

**Ответ:** Та же структура, что и у `/lesson/evaluate`.

#### 3. POST /lesson/exercises/{exercise_id}/suggestions/{word_id}

Добавление или игнорирование подсказки.

**Вход:**
```json
{
  "action": "add" | "ignore"
}
```

**Логика для `add`:**
1. Создание `user_words`:
   - `status = active`
   - `stage = 0`
   - `due_lesson_number = lesson_number + 1`
   - `source = suggestion`
2. Использование `ON CONFLICT DO NOTHING`
3. Если запись уже есть в другом статусе → 409 `already_in_vocabulary`
4. Создание записи в `lesson_exercise_words`:
   - `is_target = false`
   - `result = NULL`
   - `surface_form = NULL`
5. Подсказка получает `state = added`
6. Событие `new_word_accepted`

**Логика для `ignore`:**
1. Создание `user_words`:
   - `status = ignored`
   - `stage = 0`
   - `due_lesson_number = NULL`
   - `source = decline`
2. Подсказка получает `state = ignored`
3. Событие `new_word_declined`

**Идемпотентность:** Повтор того же действия возвращает успех без изменений.

#### 4. POST /lesson/exercises/{exercise_id}/report

Жалоба на предложение.

**Вход:**
```json
{
  "reason": "bad_sentence" | "wrong_translation" | "grammar_error" | "other",
  "comment": "Описание проблемы"
}
```

**Логика:**
1. Проверка принадлежности упражнения пользователю
2. Статус урока может быть любым
3. Одна жалоба на пользователя и упражнение
4. Повторная отправка обновляет причину и комментарий
5. Сохранение в `sentence_reports`:
   - `user_id`, `exercise_id`, `reason`, `comment`
   - `status = new`
   - `created_at`
6. Событие `report_sent`

### Rate Limiting

- 30 запросов в минуту на пользователя для `/lesson/evaluate`

## Frontend

### ExercisePage (`/lesson/:lessonId/exercise/:exerciseId`)

**Компоненты:**
1. **Прогресс-бар:** "Упражнение k из m"
2. **Крупный текст предложения**
3. **Многострочное поле ввода** (1-500 символов)
4. **Кнопка "Проверить"** — блокируется при пустом поле
5. **Кнопка "Не знаю"**
6. **Кнопка "Пожаловаться на предложение"**

**Особенности:**
- Нижняя навигация скрыта
- Кнопка "Назад" скрыта
- Черновик сохраняется в `localStorage` по ключу упражнения
- Черновик очищается после оценки
- Перехват `popstate` и `beforeunload` для модального окна выхода
- Спиннер во время проверки
- Поле ввода блокируется во время проверки

**Обработка ошибок:**
- При ошибке сервера: тост "Сервер перегружен, попробуйте ещё раз"
- Введённый текст сохраняется
- Упражнение остаётся `pending`
- При отказе модели: "Не удалось проверить перевод, попробуйте изменить формулировку"
- При исчерпании квоты: "Сервис временно недоступен"

### ReviewPage (`/lesson/:lessonId/review/:exerciseId`)

**Компоненты:**
1. **Исходное предложение**
2. **Перевод пользователя**
3. **Подсветка целевых слов:**
   - correct → зелёный
   - typo → оранжевый
   - incorrect → красный
4. **Для каждого слова:**
   - `user_fragment` или "не переведено"
   - Переводы целевого слова
5. **Эталонный перевод** под спойлером
6. **Блок "Новые слова":**
   - Каждая подсказка с переводом
   - Кнопка "+ Добавить"
   - Кнопка "× Не предлагать"
   - Нажатие сохраняется сразу
   - Повторный клик безопасен
   - Неотмеченные подсказки ничего не создают
7. **Кнопка "Далее"** — к следующему упражнению или на итоги
8. **Кнопка "Пожаловаться на предложение"**

**Анимация:** Переход упражнение → разбор: `slide-up` или `flip`

## Тесты

### Unit-тесты SRS (`tests/test_srs_service.py`)

Все 12 тестовых случаев из ТЗ + дополнительные проверки:
- Невалидные стадии (отрицательные, > 6)
- Разные номера уроков
- Интервалы для каждой стадии

## Критерии приёмки

✅ Все строки таблицы SRS покрыты тестами  
✅ Пустой ввод блокирует "Проверить"  
✅ "Не знаю" ставит всем словам `incorrect` без LLM  
✅ Повторная оценка не меняет SRS дважды  
✅ Ошибка LLM сохраняет введённый текст  
✅ Подсказки добавляются и скрываются идемпотентно  
✅ Жалоба создаётся и обновляется идемпотентно  
✅ Разбор корректно восстанавливается после перезагрузки через GET result  
✅ Транзакция не держится во время LLM-запроса  
✅ Все проверки выполняются в правильном порядке  
✅ События создаются корректно

## Пример использования

```bash
# 1. Оценить перевод
curl -X POST http://localhost:8000/lesson/evaluate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "exercise_id": 10,
    "user_translation": "Кот бегает быстро",
    "dont_know": false
  }'

# 2. Получить результат (для восстановления экрана)
curl http://localhost:8000/lesson/1/exercises/10/result \
  -H "Authorization: Bearer <token>"

# 3. Добавить подсказку
curl -X POST http://localhost:8000/lesson/exercises/10/suggestions/40 \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"action": "add"}'

# 4. Пожаловаться на предложение
curl -X POST http://localhost:8000/lesson/exercises/10/report \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "bad_sentence",
    "comment": "Предложение неестественное"
  }'
```

## Следующие части

- **Часть 11:** Жалобы на предложения (админ-интерфейс)
- **Часть 12:** Профиль пользователя и настройки
- **Часть 13:** Словарь пользователя

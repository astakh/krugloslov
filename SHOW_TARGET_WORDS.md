# ✅ Добавлено отображение целевых слов на странице упражнения

## Что было добавлено

На странице упражнения (ExercisePage) теперь отображаются целевые слова, которые нужно перевести в данном упражнении.

## Изменения

### Backend

#### 1. Схема ответа (`backend/app/schemas/lesson_evaluate.py`)

Добавлена новая схема `TargetWordInfo`:

```python
class TargetWordInfo(BaseModel):
    """Target word information for exercise."""
    word_id: int
    lemma: str
    pos: str
```

Обновлена схема `ExerciseInfoResponse`:

```python
class ExerciseInfoResponse(BaseModel):
    """Response for getting exercise info."""
    exercise_id: int
    lesson_id: int
    order_index: int
    total_exercises: int
    target_sentence: str
    status: str  # pending or evaluated
    target_words: List[TargetWordInfo]  # Target words to translate
```

#### 2. Сервис (`backend/app/services/lesson_exercise_service.py`)

Обновлён метод `get_exercise_info()` для загрузки и возврата целевых слов:

```python
# Get target words with eager loading
from app.schemas.lesson_evaluate import TargetWordInfo
result = await self.session.execute(
    select(LessonExerciseWord, Word)
    .join(Word, LessonExerciseWord.word_id == Word.id)
    .where(
        LessonExerciseWord.exercise_id == exercise_id,
        LessonExerciseWord.is_target == True
    )
    .options(selectinload(LessonExerciseWord.word))
)
target_words = [
    TargetWordInfo(
        word_id=exercise_word.word_id,
        lemma=exercise_word.word.lemma,
        pos=exercise_word.word.pos
    )
    for exercise_word, word in result.all()
]

return ExerciseInfoResponse(
    # ... other fields
    target_words=target_words
)
```

### Frontend

#### 1. Типы (`src/types/lesson.ts`)

Добавлен интерфейс `TargetWord`:

```typescript
export interface TargetWord {
  word_id: number;
  lemma: string;
  pos: string;
}

export interface Exercise {
  // ... existing fields
  target_words: TargetWord[];
}
```

#### 2. Страница упражнения (`src/pages/ExercisePage.tsx`)

Добавлен блок отображения целевых слов:

```tsx
{/* Target words */}
{exercise.target_words && exercise.target_words.length > 0 && (
  <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
    <h3 className="text-sm font-medium text-gray-700 mb-3">
      Целевые слова для перевода:
    </h3>
    <div className="flex flex-wrap gap-2">
      {exercise.target_words.map((word) => (
        <span
          key={word.word_id}
          className="inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium bg-blue-100 text-blue-800"
        >
          {word.lemma}
          <span className="ml-1.5 text-xs text-blue-600">({word.pos})</span>
        </span>
      ))}
    </div>
  </div>
)}
```

## Как это выглядит

На странице упражнения теперь отображается:

1. **Заголовок** с номером упражнения и прогресс-баром
2. **Предложение для перевода** (английский текст)
3. **Целевые слова** (новые!) - список слов в виде тегов:
   - Каждое слово отображается как `lemma (pos)`
   - Например: `house (noun)`, `run (verb)`, `fast (adjective)`
   - Слова отображаются в виде синих тегов
4. **Поле ввода перевода**
5. **Кнопки** "Проверить" и "Не знаю"

## Пример отображения

```
┌─────────────────────────────────────────┐
│ Упражнение 2 из 4                       │
│ ████████░░░░░░░░░░░░░░ 50%              │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Переведите предложение:                 │
│                                         │
│ The children play in the house.         │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Целевые слова для перевода:             │
│                                         │
│ [play (verb)] [house (noun)]            │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Ваш перевод:                            │
│                                         │
│ [________________________________]      │
│                                         │
│                              0 / 500    │
└─────────────────────────────────────────┘

[      Проверить      ] [ Не знаю ]
```

## Преимущества

✅ **Помощь пользователю** - видно, какие слова нужно перевести  
✅ **Без переводов** - показываются только lemma и pos, без русских переводов  
✅ **Наглядность** - слова отображаются в виде тегов  
✅ **Мотивация** - пользователь понимает, на что обращать внимание  

## Проверка

### Шаг 1: Перезапустите backend

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Шаг 2: Перезапустите frontend

```bash
npm run dev
```

### Шаг 3: Проверьте страницу упражнения

1. Откройте http://localhost:3000
2. Начните урок
3. Перейдите к упражнению
4. **Ожидание:** Под предложением для перевода отображается блок "Целевые слова для перевода"
5. **Ожидание:** Слова отображаются в виде синих тегов с lemma и pos

### Шаг 4: Проверьте API

```bash
# Получите токен
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "yourpassword"}' \
  | jq -r '.access_token')

# Получите информацию об упражнении
curl -X GET "http://localhost:8000/lesson/1/exercises/1" \
  -H "Authorization: Bearer $TOKEN"
```

**Ожидаемый ответ:**
```json
{
  "exercise_id": 1,
  "lesson_id": 1,
  "order_index": 0,
  "total_exercises": 4,
  "target_sentence": "The children play in the house.",
  "status": "pending",
  "target_words": [
    {
      "word_id": 26,
      "lemma": "play",
      "pos": "verb"
    },
    {
      "word_id": 7,
      "lemma": "house",
      "pos": "noun"
    }
  ]
}
```

## Изменённые файлы

### Backend
1. ✅ `backend/app/schemas/lesson_evaluate.py` - добавлена схема `TargetWordInfo`
2. ✅ `backend/app/services/lesson_exercise_service.py` - обновлён метод `get_exercise_info()`

### Frontend
1. ✅ `src/types/lesson.ts` - добавлен интерфейс `TargetWord`
2. ✅ `src/pages/ExercisePage.tsx` - добавлено отображение целевых слов

## Документация

- `SHOW_TARGET_WORDS.md` - этот файл

## Статус

✅ Backend обновлён  
✅ Frontend обновлён  
✅ Проект пересобран  
✅ Готово к использованию  

## Следующие шаги

1. ✅ Перезапустите backend
2. ✅ Перезапустите frontend
3. ✅ Начните урок
4. ✅ Проверьте, что целевые слова отображаются на странице упражнения

Теперь пользователи видят, какие слова нужно перевести в каждом упражнении! 🎉

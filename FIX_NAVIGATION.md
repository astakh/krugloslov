# ✅ Исправлена навигация на экран упражнения

## Проблема

После создания урока пользователь видел заглушку "Экран прохождения урока (будет реализован)" вместо реального упражнения.

## Причина

В `LessonPreviewPage.tsx` была неправильная навигация:

1. **После создания урока:** переход на `/lesson/${lesson_id}` (неправильно)
2. **При state === "resume":** переход на `/lesson/resume` (неправильно)

Правильные URL:
- Упражнение: `/lesson/:lessonId/exercise/:exerciseId`
- Resume: `/lesson/:lessonId/resume`

## Решение

### 1. Исправлена навигация после создания урока

**Файл:** `src/pages/LessonPreviewPage.tsx`

**Было:**
```typescript
const data = await response.json();

// Navigate to lesson
navigate(`/lesson/${data.lesson_id}`);
```

**Стало:**
```typescript
const data = await response.json();

// Navigate to first exercise
navigate(`/lesson/${data.lesson_id}/exercise/${data.current_exercise.exercise_id}`);
```

### 2. Обновлен интерфейс PreviewData

**Было:**
```typescript
interface PreviewData {
  state: "ready" | "resume" | "limit_reached" | "no_words";
  lesson_number?: number;
  due_words?: WordInfo[];
  new_words?: WordInfo[];
  dictionary_exhausted?: boolean;
}
```

**Стало:**
```typescript
interface PreviewData {
  state: "ready" | "resume" | "limit_reached" | "no_words";
  lesson_number?: number;
  lesson_id?: number;
  exercises_done?: number;
  exercises_total?: number;
  resets_at?: string;
  due_words?: WordInfo[];
  new_words?: WordInfo[];
  dictionary_exhausted?: boolean;
}
```

### 3. Исправлена навигация при state === "resume"

**Было:**
```typescript
{preview?.state === "resume" && (
  <>
    <div className="text-5xl mb-4">▶️</div>
    <h2 className="text-xl font-bold mb-2">Есть незавершённый урок</h2>
    <p className="text-gray-600 mb-4">Продолжите предыдущий урок</p>
    <button
      onClick={() => navigate("/lesson/resume")}
      className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
    >
      Продолжить
    </button>
  </>
)}
```

**Стало:**
```typescript
{preview?.state === "resume" && preview.lesson_id && (
  <>
    <div className="text-5xl mb-4">▶️</div>
    <h2 className="text-xl font-bold mb-2">Есть незавершённый урок</h2>
    <p className="text-gray-600 mb-4">
      Выполнено {preview.exercises_done} из {preview.exercises_total} упражнений
    </p>
    <button
      onClick={() => navigate(`/lesson/${preview.lesson_id}/resume`)}
      className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
    >
      Продолжить
    </button>
  </>
)}
```

## Проверка исправления

### Шаг 1: Перезапустите frontend

Frontend уже пересобран. Если нужно пересобрать вручную:

```bash
npm run build
```

Или для разработки:

```bash
npm run dev
```

### Шаг 2: Проверьте создание урока

1. Откройте http://localhost:3000
2. Войдите в систему
3. Нажмите "Начать урок"
4. Выберите слова
5. Нажмите "Поехали!"
6. **Ожидание:** Переход на `/lesson/{lesson_id}/exercise/{exercise_id}`
7. **Ожидание:** Отображается ExercisePage с предложением для перевода

### Шаг 3: Проверьте возобновление урока

1. Создайте урок
2. Перейдите к упражнению
3. Вернитесь на главную (не завершая урок)
4. Нажмите "Продолжить урок"
5. **Ожидание:** Переход на `/lesson/{lesson_id}/resume`
6. **Ожидание:** Отображается ResumePage с информацией о прогрессе
7. Нажмите "Продолжить"
8. **Ожидание:** Переход на `/lesson/{lesson_id}/exercise/{exercise_id}`

## Маршруты

### Правильные URL:

- **Предпросмотр урока:** `/lesson/preview`
- **Создание урока:** POST `/lesson/start` → переход на `/lesson/{id}/exercise/{exercise_id}`
- **Возобновление урока:** `/lesson/{lessonId}/resume`
- **Упражнение:** `/lesson/{lessonId}/exercise/{exerciseId}`
- **Разбор результатов:** `/lesson/{lessonId}/review/{exerciseId}`
- **Итоги урока:** `/lesson/{lessonId}/complete` или `/lesson/{lessonId}/summary`

### Неправильные URL (больше не используются):

- ❌ `/lesson/{id}` - нет такого маршрута
- ❌ `/lesson/resume` - нет lesson_id

## Измененные файлы

1. ✅ `src/pages/LessonPreviewPage.tsx`
   - Исправлена навигация после создания урока
   - Обновлен интерфейс PreviewData
   - Исправлена навигация при state === "resume"

## Документация

- `FIX_NAVIGATION.md` - этот файл

## Статус

✅ Навигация исправлена  
✅ Frontend пересобран  
✅ Готово к использованию  

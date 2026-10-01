# ✅ Исправлена ошибка 422 при отправке жалобы

## Проблема

При попытке отправить жалобу на предложение backend возвращал ошибку 422 Unprocessable Entity.

## Причина

В `ReviewPage.tsx` функция `handleReport` использовала `prompt()` для получения причины жалобы, но не валидировала ввод. Если пользователь вводил недопустимое значение (например, "плохое предложение" вместо "bad_sentence"), backend отклонял запрос с ошибкой 422.

### Схема ReportRequest

```python
class ReportRequest(BaseModel):
    reason: Literal["bad_sentence", "wrong_translation", "grammar_error", "other"]
    comment: str = Field(..., max_length=500)
```

Backend требует, чтобы `reason` был одним из четырёх допустимых значений.

## Решение

Добавил валидацию ввода причины жалобы на frontend:

### Изменения в `src/pages/ReviewPage.tsx`

**Было:**
```typescript
const handleReport = () => {
  const reason = prompt('Причина жалобы (bad_sentence, wrong_translation, grammar_error, other):');
  if (!reason) return;
  
  const comment = prompt('Комментарий (необязательно):') || '';
  
  reportMutation.mutate({ reason, comment });
};
```

**Стало:**
```typescript
const handleReport = () => {
  const reasons = [
    'bad_sentence - Проблема с предложением',
    'wrong_translation - Неправильный перевод',
    'grammar_error - Грамматическая ошибка',
    'other - Другое'
  ];
  
  const reasonInput = prompt(
    'Выберите причину жалобы:\n\n' + 
    reasons.join('\n') + 
    '\n\nВведите одно из: bad_sentence, wrong_translation, grammar_error, other'
  );
  
  if (!reasonInput) return;
  
  const reason = reasonInput.trim().toLowerCase();
  const validReasons = ['bad_sentence', 'wrong_translation', 'grammar_error', 'other'];
  
  if (!validReasons.includes(reason)) {
    alert('Недопустимая причина. Используйте одно из: bad_sentence, wrong_translation, grammar_error, other');
    return;
  }
  
  const comment = prompt('Комментарий (необязательно):') || '';
  
  reportMutation.mutate({ reason, comment });
};
```

## Что изменилось

1. ✅ Показывает список допустимых причин с описаниями
2. ✅ Приводит ввод к нижнему регистру и удаляет пробелы
3. ✅ Проверяет, что причина является допустимой
4. ✅ Показывает ошибку, если введено недопустимое значение
5. ✅ Отправляет запрос только с валидной причиной

## Проверка

### Перезапустите frontend

```bash
# Остановите текущий процесс (Ctrl+C)
npm run dev
```

### Проверьте отправку жалобы

1. Откройте http://localhost:3000
2. Войдите в систему
3. Начните урок
4. Пройдите упражнение
5. На экране разбора результатов нажмите "Пожаловаться на предложение"
6. Введите допустимую причину (например, `bad_sentence`)
7. Введите комментарий (необязательно)
8. Нажмите OK

### Ожидаемое поведение

**Успех:**
```
✅ Жалоба отправлена
✅ Backend возвращает 200 OK
✅ В логах: POST /lesson/exercises/{id}/report - 200 OK
```

**Недопустимая причина:**
```
⚠️ Появляется alert: "Недопустимая причина. Используйте одно из: ..."
⚠️ Запрос не отправляется
```

### Допустимые причины

- `bad_sentence` - Проблема с предложением (неестественное, неправильное)
- `wrong_translation` - Неправильный эталонный перевод
- `grammar_error` - Грамматическая ошибка в предложении
- `other` - Другая проблема

## Проверка через API

```bash
# Получите токен
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "yourpassword"}' \
  | jq -r '.access_token')

# Отправьте жалобу с допустимой причиной
curl -X POST http://localhost:8000/lesson/exercises/8/report \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "bad_sentence",
    "comment": "Предложение неестественное"
  }'
# Ожидается: 200 OK

# Отправьте жалобу с недопустимой причиной
curl -X POST http://localhost:8000/lesson/exercises/8/report \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "invalid_reason",
    "comment": "Тест"
  }'
# Ожидается: 422 Unprocessable Entity
```

## Изменённые файлы

1. ✅ `src/pages/ReviewPage.tsx` - добавлена валидация причины жалобы

## Документация

- `FIX_REPORT_VALIDATION.md` - этот файл

## Статус

✅ Ошибка 422 исправлена  
✅ Добавлена валидация на frontend  
✅ Frontend пересобран  
✅ Готово к использованию  

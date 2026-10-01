# Исправление ошибки advisory_lock

## Проблема

При запуске урока возникала ошибка:

```
TypeError: 'coroutine' object does not support the asynchronous context manager protocol
```

**Трассировка:**
```
File "D:\krugoslov\backend\app\services\lesson_start_service.py", line 80, in start_lesson
    async with self._advisory_lock(profile.id):
TypeError: 'coroutine' object does not support the asynchronous context manager protocol
```

## Причина

Метод `_advisory_lock` был определен как `async def`:

```python
async def _advisory_lock(self, profile_id: int):
    """Context manager for advisory lock."""
    class AdvisoryLockContext:
        async def __aenter__(self):
            # ...
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            # ...
    
    return AdvisoryLockContext(self.session, profile_id)
```

Проблема в том, что `async def` создает coroutine object, а не контекстный менеджер. Когда мы пытаемся использовать его с `async with`, Python ожидает объект с методами `__aenter__` и `__aexit__`, но получает coroutine.

## Решение

Изменить метод `_advisory_lock` с `async def` на обычный `def`:

```python
def _advisory_lock(self, profile_id: int):
    """Context manager for advisory lock."""
    class AdvisoryLockContext:
        async def __aenter__(self):
            # ...
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            # ...
    
    return AdvisoryLockContext(self.session, profile_id)
```

**Почему это работает:**
- Метод `_advisory_lock` сам по себе не выполняет асинхронных операций
- Он только создает и возвращает объект контекстного менеджера
- Асинхронные операции выполняются внутри методов `__aenter__` и `__aexit__` контекстного менеджера
- Поэтому метод должен быть обычным `def`, а не `async def`

## Исправленный файл

**Файл:** `backend/app/services/lesson_start_service.py`

**Строка:** 283

**Изменение:**
```diff
- async def _advisory_lock(self, profile_id: int):
+ def _advisory_lock(self, profile_id: int):
```

## Проверка

После исправления:
1. Перезапустите backend сервер
2. Попробуйте начать урок
3. Ошибка должна исчезнуть
4. Advisory lock должен работать корректно

## Дополнительная информация

### Как работает advisory lock

1. **Создание контекстного менеджера:**
   ```python
   async with self._advisory_lock(profile.id):
       # ... код внутри блокировки
   ```

2. **Получение блокировки (`__aenter__`):**
   ```python
   result = await self.session.execute(
       text(f"SELECT pg_try_advisory_xact_lock(:id)"),
       {"id": self.profile_id}
   )
   self.locked = result.scalar_one()
   ```

3. **Освобождение блокировки (`__aexit__`):**
   - Блокировка автоматически освобождается при завершении транзакции
   - Не требует явного вызова

### Зачем нужен advisory lock

- Предотвращает параллельный запуск уроков для одного пользователя
- Использует PostgreSQL advisory locks
- Автоматически освобождается при завершении транзакции
- Возвращает ошибку 409 если блокировка не получена

## Статус

✅ Исправлено  
✅ Проект пересобран  
✅ Готово к использованию  

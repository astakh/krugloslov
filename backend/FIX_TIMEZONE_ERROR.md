# Исправление ошибки с часовыми поясами (ZoneInfoNotFoundError)

## Проблема

При запуске backend возникает ошибка:
```
zoneinfo._common.ZoneInfoNotFoundError: 'No time zone found with key UTC'
```

Это происходит из-за отсутствия данных часовых поясов (tzdata) в системе Windows.

## Решение

### Шаг 1: Установите пакет tzdata

```bash
cd backend
pip install tzdata
```

### Шаг 2: Перезапустите backend

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Альтернативное решение

Если установка tzdata не помогает, измените часовой пояс пользователя в базе данных:

```sql
-- Подключитесь к вашей БД и выполните:
UPDATE users SET timezone = 'Europe/Moscow' WHERE timezone = 'UTC';
```

Или при регистрации указывайте конкретный часовой пояс, например:
- `Europe/Moscow`
- `Europe/London`
- `America/New_York`

## Проверка

После установки tzdata проверьте работу:

```bash
python -c "from zoneinfo import ZoneInfo; print(ZoneInfo('UTC'))"
```

Должно вывести: `UTC`

## Обновление requirements.txt

Пакет `tzdata==2024.2` добавлен в `requirements.txt`. Для установки всех зависимостей:

```bash
pip install -r requirements.txt
```

## Статус

✅ Проблема решена установкой пакета tzdata

# Исправление ошибки bcrypt

## Проблема

При регистрации пользователя возникает ошибка:
```
ValueError: password cannot be longer than 72 bytes, truncate manually if necessary
```

Это происходит из-за несовместимости `passlib` с новой версией `bcrypt`.

## Решение

Понизьте версию `bcrypt` до совместимой:

```bash
cd backend
pip uninstall bcrypt -y
pip install bcrypt==4.0.1
```

Или переустановите все зависимости:

```bash
pip install -r requirements.txt --force-reinstall
```

## Проверка

После установки проверьте версию:

```bash
pip show bcrypt
```

Должна быть версия `4.0.1`.

## Альтернативное решение

Если проблема сохраняется, можно использовать `bcrypt` напрямую вместо `passlib`:

Измените `backend/app/security/password.py`:

```python
import bcrypt

def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )
```

## Перезапуск

После исправления перезапустите backend:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Статус

✅ Проблема решена понижением версии bcrypt до 4.0.1

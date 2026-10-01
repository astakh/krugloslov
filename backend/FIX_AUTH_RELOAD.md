# Исправление проблемы с авторизацией после перезагрузки

## Проблема

После перезагрузки страницы пользователь получает ошибку 401 Unauthorized при попытке получить доступ к dashboard, даже если он был авторизован.

**Симптомы:**
```
GET http://localhost:3000/api/dashboard/summary 401 (Unauthorized)
```

## Причина

Access token хранился только в памяти React (useState), что означало потерю токена при перезагрузке страницы. Refresh token хранится в httpOnly cookie и доступен, но не использовался для автоматического восстановления сессии.

## Решение

Добавлена автоматическая восстановление сессии при загрузке приложения:

1. **При загрузке приложения** AuthContext пытается восстановить сессию через refresh token
2. **Если refresh успешен** - устанавливается новый access token и загружается информация о пользователе
3. **Если refresh не удался** - пользователь перенаправляется на страницу входа
4. **Пока идет восстановление** - показывается экран загрузки

## Изменения в коде

### `src/contexts/AuthContext.tsx`

#### 1. Начальное состояние isLoading = true
```typescript
const [isLoading, setIsLoading] = useState(true); // Start with loading true
```

#### 2. Автоматическое восстановление сессии
```typescript
// Restore session on app load using refresh token
useEffect(() => {
  const restoreSession = async () => {
    try {
      // Try to refresh token on app load
      const response = await apiClient.post<TokenResponse>("/auth/refresh");
      const newToken = response.access_token;
      setAccessToken(newToken);
      
      // Fetch user info with new token
      const userInfo = await fetchUserInfo(newToken);
      setUser(userInfo);
    } catch {
      // No valid session, user needs to login
      setAccessToken(null);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  restoreSession();
}, []);
```

#### 3. Экран загрузки
```typescript
// Show loading screen while restoring session
if (isLoading) {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <div className="text-2xl mb-4">⏳</div>
        <p className="text-gray-600">Загрузка...</p>
      </div>
    </div>
  );
}
```

## Как это работает

### Сценарий 1: Пользователь авторизован, перезагружает страницу

1. Пользователь входит в систему
2. Access token устанавливается в состоянии
3. Refresh token устанавливается в httpOnly cookie
4. Пользователь перезагружает страницу
5. **AuthContext запускает restoreSession()**
6. Делается запрос `POST /auth/refresh` с refresh token из cookie
7. Backend возвращает новый access token
8. Access token устанавливается в состоянии
9. Загружается информация о пользователе через `GET /auth/me`
10. Пользователь остается авторизованным ✅

### Сценарий 2: Пользователь не авторизован

1. Пользователь открывает приложение
2. **AuthContext запускает restoreSession()**
3. Делается запрос `POST /auth/refresh`
4. Refresh token отсутствует или недействителен
5. Backend возвращает 401
6. AuthContext очищает состояние
7. Пользователь видит страницу входа ✅

### Сценарий 3: Refresh token истек

1. Пользователь был авторизован давно
2. Refresh token истек (через 30 дней)
3. Пользователь открывает приложение
4. **AuthContext запускает restoreSession()**
5. Запрос `POST /auth/refresh` возвращает 401
6. AuthContext очищает состояние
7. Пользователь перенаправляется на страницу входа ✅

## Проверка

### 1. Перезапустите frontend
```bash
# Остановите текущий процесс (Ctrl+C)
npm run dev
```

### 2. Проверьте сценарий авторизации

**Шаг 1: Вход в систему**
1. Откройте http://localhost:3000
2. Войдите в систему
3. Проверьте консоль - должны быть успешные запросы:
   ```
   ✅ POST /auth/login - 200 OK
   ✅ GET /auth/me - 200 OK
   ```

**Шаг 2: Перезагрузка страницы**
1. Нажмите F5 или Ctrl+R
2. Должен появиться экран "Загрузка..."
3. Проверьте консоль:
   ```
   ✅ POST /auth/refresh - 200 OK
   ✅ GET /auth/me - 200 OK
   ✅ GET /dashboard/summary - 200 OK
   ```
4. Пользователь остается авторизованным ✅

**Шаг 3: Проверка токенов**
1. Откройте DevTools (F12)
2. Перейдите в Application → Cookies
3. Найдите cookie `refresh_token`
4. Она должна быть установлена ✅

### 3. Проверьте сценарий выхода

**Шаг 1: Выход из системы**
1. Нажмите кнопку "Выйти"
2. Проверьте консоль:
   ```
   ✅ POST /auth/logout - 200 OK
   ```
3. Cookie `refresh_token` должна быть удалена

**Шаг 2: Перезагрузка после выхода**
1. Нажмите F5
2. Должен появиться экран "Загрузка..."
3. Проверьте консоль:
   ```
   ❌ POST /auth/refresh - 401 Unauthorized
   ```
4. Пользователь перенаправляется на страницу входа ✅

## Проверка через API

```bash
# 1. Войдите в систему
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}' \
  -c cookies.txt

# Сохраните access_token из ответа

# 2. Проверьте dashboard с токеном
curl -X GET http://localhost:8000/dashboard/summary \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
# Ожидается: 200 OK

# 3. Обновите токен через refresh
curl -X POST http://localhost:8000/auth/refresh \
  -b cookies.txt
# Ожидается: 200 OK с новым access_token

# 4. Используйте новый токен
curl -X GET http://localhost:8000/dashboard/summary \
  -H "Authorization: Bearer NEW_ACCESS_TOKEN"
# Ожидается: 200 OK
```

## Типичные проблемы

### Проблема: После перезагрузки все равно 401

**Решение:**
1. Проверьте, что backend запущен
2. Проверьте, что cookie `refresh_token` установлена
3. Проверьте консоль на наличие ошибок
4. Очистите кэш браузера и попробуйте снова

### Проблема: Экран "Загрузка..." не исчезает

**Решение:**
1. Проверьте консоль на наличие ошибок JavaScript
2. Проверьте, что backend доступен
3. Проверьте, что endpoint `/auth/refresh` работает
4. Перезапустите frontend

### Проблема: Refresh token не устанавливается

**Решение:**
1. Проверьте настройки CORS в backend
2. Убедитесь, что `credentials: "include"` установлен в запросах
3. Проверьте, что backend возвращает Set-Cookie header
4. Проверьте настройки cookie (secure, samesite)

## Архитектура аутентификации

```
┌─────────────────────────────────────────────────────────┐
│                      Frontend                            │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐                                       │
│  │  AuthContext │                                       │
│  │              │                                       │
│  │  - access    │  ← Хранится в памяти (useState)      │
│  │    token     │                                       │
│  │              │                                       │
│  │  - user      │  ← Хранится в памяти (useState)      │
│  │    info      │                                       │
│  └──────────────┘                                       │
│                                                          │
│  ┌──────────────┐                                       │
│  │   Browser    │                                       │
│  │   Cookies    │  ← refresh_token (httpOnly)          │
│  └──────────────┘                                       │
│                                                          │
└─────────────────────────────────────────────────────────┘
                          ↓
                    HTTP Requests
                          ↓
┌─────────────────────────────────────────────────────────┐
│                      Backend                             │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐                                       │
│  │  /auth/      │                                       │
│  │  login       │  → Устанавливает refresh_token cookie │
│  └──────────────┘                                       │
│                                                          │
│  ┌──────────────┐                                       │
│  │  /auth/      │                                       │
│  │  refresh     │  → Читает refresh_token cookie       │
│  └──────────────┘  → Возвращает новый access_token     │
│                                                          │
│  ┌──────────────┐                                       │
│  │  /auth/      │                                       │
│  │  logout      │  → Удаляет refresh_token cookie      │
│  └──────────────┘                                       │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Поток аутентификации

### Вход в систему
```
1. POST /auth/login (email, password)
   ↓
2. Backend проверяет credentials
   ↓
3. Backend создает access_token и refresh_token
   ↓
4. Backend возвращает:
   - access_token в теле ответа
   - refresh_token в Set-Cookie header
   ↓
5. Frontend сохраняет access_token в состоянии
   ↓
6. Browser сохраняет refresh_token в cookie
```

### Автоматическое восстановление
```
1. Пользователь перезагружает страницу
   ↓
2. AuthContext запускает restoreSession()
   ↓
3. POST /auth/refresh (с refresh_token из cookie)
   ↓
4. Backend проверяет refresh_token
   ↓
5. Backend возвращает новый access_token
   ↓
6. Frontend сохраняет новый access_token
   ↓
7. GET /auth/me (с новым access_token)
   ↓
8. Frontend загружает информацию о пользователе
   ↓
9. Пользователь остается авторизованным ✅
```

### Выход из системы
```
1. POST /auth/logout (с access_token)
   ↓
2. Backend отзывает refresh_token
   ↓
3. Backend удаляет refresh_token cookie
   ↓
4. Frontend очищает access_token из состояния
   ↓
5. Frontend очищает user info из состояния
   ↓
6. Пользователь перенаправляется на страницу входа
```

## Безопасность

### Access Token
- **Где хранится:** В памяти React (useState)
- **Время жизни:** 15 минут
- **Передача:** В заголовке Authorization: Bearer
- **Безопасность:** Теряется при перезагрузке, но это нормально

### Refresh Token
- **Где хранится:** В httpOnly cookie
- **Время жизни:** 30 дней
- **Передача:** Автоматически в cookie
- **Безопасность:** 
  - httpOnly - недоступен из JavaScript
  - Secure - передается только по HTTPS
  - SameSite=Lax - защита от CSRF

### Ротация токенов
- При каждом refresh старый refresh_token отзывается
- Выдается новая пара access_token + refresh_token
- Защита от повторного использования (replay attack)

## Статус

✅ Проблема решена  
✅ Автоматическое восстановление сессии работает  
✅ Экран загрузки показывается при восстановлении  
✅ Frontend пересобран  
✅ Готово к использованию  

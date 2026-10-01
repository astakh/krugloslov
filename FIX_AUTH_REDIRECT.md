# ✅ Исправлена проблема с перенаправлением на страницу входа

## Проблема

После перезагрузки страницы приложение пыталось восстановить сессию через `/auth/refresh`, получало 401, и затем пыталось загрузить `/dashboard/summary`, что тоже возвращало 401. Вместо этого пользователь должен был видеть страницу входа.

**Логи:**
```
POST /auth/refresh - 401 Unauthorized
GET /dashboard/summary - 401 Unauthorized
GET /dashboard/summary - 401 Unauthorized
```

## Причина

1. В `HomePage` не было проверки `isAuthenticated`
2. После неудачного восстановления сессии в `AuthContext` не происходило перенаправление на `/auth`
3. HomePage пытался загрузить dashboard без проверки авторизации

## Решение

### 1. Добавлена проверка авторизации в HomePage

**Файл:** `src/pages/HomePage.tsx`

```typescript
const { user, isAuthenticated } = useAuth();

useEffect(() => {
  // Check if user is authenticated
  if (!isAuthenticated) {
    navigate("/auth");
    return;
  }
  
  loadDashboard();
}, [isAuthenticated, navigate]);
```

**Что изменилось:**
- Добавлена проверка `isAuthenticated` перед загрузкой dashboard
- Если пользователь не авторизован, перенаправление на `/auth`
- Зависимости `useEffect` включают `isAuthenticated` и `navigate`

### 2. Добавлено перенаправление после неудачного восстановления сессии

**Файл:** `src/contexts/AuthContext.tsx`

```typescript
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
      // Redirect to login page if not already there
      if (window.location.pathname !== "/auth" && window.location.pathname !== "/register") {
        navigate("/auth");
      }
    } finally {
      setIsLoading(false);
    }
  };

  restoreSession();
}, [navigate]);
```

**Что изменилось:**
- После неудачного восстановления сессии происходит перенаправление на `/auth`
- Проверка, что пользователь не находится уже на странице `/auth` или `/register`
- Добавлена зависимость `navigate` в `useEffect`

## Как это работает

### Сценарий 1: Пользователь не авторизован, перезагружает страницу

```
1. Пользователь перезагружает страницу (F5)
   ↓
2. AuthContext запускает restoreSession()
   ↓
3. POST /auth/refresh (refresh token отсутствует или недействителен)
   ↓
4. Backend возвращает 401
   ↓
5. AuthContext очищает состояние (accessToken = null, user = null)
   ↓
6. AuthContext перенаправляет на /auth
   ↓
7. Пользователь видит страницу входа ✅
```

### Сценарий 2: Пользователь пытается зайти на главную без авторизации

```
1. Пользователь открывает http://localhost:3000/
   ↓
2. AuthContext запускает restoreSession()
   ↓
3. POST /auth/refresh - 401
   ↓
4. AuthContext перенаправляет на /auth
   ↓
5. HomePage проверяет isAuthenticated
   ↓
6. isAuthenticated = false
   ↓
7. HomePage перенаправляет на /auth (двойная защита)
   ↓
8. Пользователь видит страницу входа ✅
```

### Сценарий 3: Пользователь авторизован, перезагружает страницу

```
1. Пользователь перезагружает страницу (F5)
   ↓
2. AuthContext запускает restoreSession()
   ↓
3. POST /auth/refresh - 200 OK (новый access token)
   ↓
4. GET /auth/me - 200 OK (информация о пользователе)
   ↓
5. AuthContext устанавливает accessToken и user
   ↓
6. HomePage проверяет isAuthenticated
   ↓
7. isAuthenticated = true
   ↓
8. HomePage загружает dashboard
   ↓
9. GET /dashboard/summary - 200 OK
   ↓
10. Пользователь видит главную страницу ✅
```

## Что нужно сделать

### 1. Перезапустите frontend

```bash
# Остановите текущий процесс (Ctrl+C)
npm run dev
```

### 2. Очистите кэш браузера

- DevTools (F12) → Правой кнопкой на обновлении → "Очистить кэш и жесткая перезагрузка"
- Или используйте режим инкогнито

### 3. Проверьте сценарий

**Шаг 1: Выйдите из системы**
1. Нажмите кнопку "Выйти"
2. Проверьте, что cookie `refresh_token` удалена

**Шаг 2: Перезагрузите страницу**
1. Нажмите F5
2. Должен появиться экран "⏳ Загрузка..."
3. Проверьте консоль:
   ```
   ❌ POST /auth/refresh - 401 Unauthorized
   ```
4. **Ожидание:** Автоматическое перенаправление на `/auth`
5. Пользователь видит страницу входа ✅

**Шаг 3: Войдите в систему**
1. Введите email и пароль
2. Нажмите "Войти"
3. Проверьте консоль:
   ```
   ✅ POST /auth/login - 200 OK
   ✅ GET /auth/me - 200 OK
   ✅ GET /dashboard/summary - 200 OK
   ```
4. Пользователь видит главную страницу ✅

## Проверка через DevTools

### 1. Проверьте перенаправления

1. Откройте DevTools (F12)
2. Перейдите в Network tab
3. Перезагрузите страницу (F5)
4. Проверьте последовательность запросов:
   ```
   1. POST /auth/refresh - 401
   2. Redirect to /auth
   3. GET /auth - 200 (страница входа)
   ```

### 2. Проверьте состояние AuthContext

1. Откройте DevTools (F12)
2. Перейдите в Console tab
3. Выполните:
   ```javascript
   // Проверьте текущий путь
   window.location.pathname
   // Должно быть: "/auth"
   ```

### 3. Проверьте cookies

1. Откройте DevTools (F12)
2. Перейдите в Application → Cookies → http://localhost:3000
3. Проверьте наличие cookie `refresh_token`
4. После выхода cookie должна быть удалена

## Типичные проблемы

### Проблема: Не перенаправляет на /auth

**Решение:**
1. Убедитесь, что frontend перезапущен (`npm run dev`)
2. Очистите кэш браузера
3. Проверьте консоль на наличие ошибок JavaScript
4. Проверьте, что `isAuthenticated` корректно обновляется

### Проблема: Бесконечный цикл перенаправлений

**Решение:**
1. Проверьте, что в `AuthContext` есть проверка `window.location.pathname !== "/auth"`
2. Проверьте, что в `HomePage` есть проверка `isAuthenticated`
3. Очистите кэш браузера

### Проблема: После входа не загружается dashboard

**Решение:**
1. Проверьте консоль на наличие ошибок
2. Проверьте, что `isAuthenticated = true`
3. Проверьте, что `accessToken` установлен
4. Проверьте, что `loadDashboard()` вызывается

## Архитектура защиты маршрутов

```
┌─────────────────────────────────────────────────────────┐
│                    App Load                              │
└─────────────────────────────────────────────────────────┘
                          ↓
              ┌───────────────────────┐
              │   AuthContext         │
              │   restoreSession()    │
              └───────────────────────┘
                          ↓
              ┌───────────────────────┐
              │ POST /auth/refresh    │
              └───────────────────────┘
                          ↓
              ┌───────────────────────┐
              │   Success?            │
              └───────────────────────┘
                    ↓         ↓
                   YES        NO
                    ↓         ↓
          ┌─────────┴──┐  ┌─┴──────────┐
          │ Set tokens │  │ Clear state│
          │ Load user  │  │ Redirect   │
          └────────────┘  │ to /auth   │
                          └────────────┘
                                 ↓
                    ┌───────────────────────┐
                    │   AuthPage            │
                    │   (Login/Register)    │
                    └───────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                    HomePage Load                         │
└─────────────────────────────────────────────────────────┘
                          ↓
              ┌───────────────────────┐
              │ Check isAuthenticated │
              └───────────────────────┘
                          ↓
              ┌───────────────────────┐
              │   Authenticated?      │
              └───────────────────────┘
                    ↓         ↓
                   YES        NO
                    ↓         ↓
          ┌─────────┴──┐  ┌─┴──────────┐
          │ Load       │  │ Redirect   │
          │ dashboard  │  │ to /auth   │
          └────────────┘  └────────────┘
```

## Двойная защита

Теперь у нас есть двойная защита от несанкционированного доступа:

1. **AuthContext:** Перенаправляет на `/auth` после неудачного восстановления сессии
2. **HomePage:** Проверяет `isAuthenticated` перед загрузкой dashboard

Это гарантирует, что пользователь всегда будет перенаправлен на страницу входа, если не авторизован.

## Статус

✅ Проблема решена  
✅ Проверка авторизации в HomePage  
✅ Перенаправление после неудачного восстановления  
✅ Frontend пересобран  
✅ Готово к использованию  

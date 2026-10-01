# Исправление проблемы с бесконечным циклом refresh

## Проблема

При перезагрузке страницы возникал бесконечный цикл попыток refresh токена:

```
POST /auth/refresh - 401 Unauthorized
POST /auth/refresh - 401 Unauthorized
POST /auth/refresh - 401 Unauthorized
...
```

Также происходило "мигание" онбординга - страница на мгновение появлялась, а затем перенаправляла на авторизацию.

## Причины

### 1. Бесконечный цикл refresh

При получении 401 ответа от любого API запроса диспатчилось событие `api:unauthorized`, которое вызывало `refreshAccessToken()`. Если refresh не удался (401), то снова диспатчилось событие, и цикл повторялся.

### 2. Мигание онбординга

В `AuthContext` был `useEffect`, который перенаправлял на онбординг, если пользователь авторизован, но не прошел онбординг. Но это перенаправление происходило даже если пользователь уже находился на странице онбординга или авторизации, что создавало цикл.

### 3. Множественные вызовы restoreSession

При каждой загрузке страницы вызывался `restoreSession()`, который пытался восстановить сессию через refresh token. Если refresh не удался, происходило перенаправление на `/auth`, но это могло конфликтовать с другими перенаправлениями.

## Решения

### 1. Защита от бесконечного цикла refresh

**Файл:** `src/api/client.ts`

Добавлена проверка, чтобы не диспатчить событие `api:unauthorized` для запросов refresh:

```typescript
// Don't dispatch unauthorized event for refresh requests to avoid infinite loop
const isRefreshRequest = path.includes("/auth/refresh");

// Only dispatch unauthorized event for 401 status, not for 409 or other errors
if (response.status === 401 && !isRefreshRequest) {
  // Dispatch event for auth context to handle
  window.dispatchEvent(new CustomEvent("api:unauthorized"));
}
```

**Файл:** `src/contexts/AuthContext.tsx`

Добавлен флаг `isRefreshing` для предотвращения множественных вызовов refresh:

```typescript
useEffect(() => {
  let isRefreshing = false;
  
  const handleUnauthorized = async () => {
    // Only try to refresh if we have an access token
    // (otherwise we're not authenticated yet)
    if (!accessToken || isRefreshing) {
      return;
    }
    
    isRefreshing = true;
    
    try {
      await refreshAccessToken();
    } catch {
      // Refresh failed, already redirected in refreshAccessToken
    } finally {
      isRefreshing = false;
    }
  };

  window.addEventListener("api:unauthorized", handleUnauthorized);
  return () => {
    window.removeEventListener("api:unauthorized", handleUnauthorized);
  };
}, [refreshAccessToken, accessToken]);
```

### 2. Исправление перенаправления на онбординг

**Файл:** `src/contexts/AuthContext.tsx`

Добавлена проверка текущего пути перед перенаправлением:

```typescript
// Redirect to onboarding if authenticated but not onboarded
useEffect(() => {
  if (user && !user.is_onboarded) {
    const currentPath = window.location.pathname;
    // Only redirect if not already on onboarding or auth pages
    if (currentPath !== "/onboarding" && currentPath !== "/auth" && currentPath !== "/register") {
      navigate("/onboarding");
    }
  }
}, [user, navigate]);
```

### 3. Защита от множественных вызовов restoreSession

**Файл:** `src/contexts/AuthContext.tsx`

Добавлен `sessionRestoredRef` для отслеживания, была ли уже попытка восстановления сессии:

```typescript
// Ref to track if session restoration has been attempted
const sessionRestoredRef = useRef(false);

// Restore session on app load using refresh token
useEffect(() => {
  // Only attempt session restoration once
  if (sessionRestoredRef.current) {
    setIsLoading(false);
    return;
  }
  
  sessionRestoredRef.current = true;

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
      // Don't redirect here - let the app handle routing based on auth state
    } finally {
      setIsLoading(false);
    }
  };

  restoreSession();
}, [fetchUserInfo]);
```

## Проверка

### 1. Перезапустите frontend

```bash
# Остановите текущий процесс (Ctrl+C)
npm run dev
```

### 2. Очистите кэш браузера

- Откройте DevTools (F12)
- Правой кнопкой на кнопке обновления → "Очистить кэш и жесткая перезагрузка"
- Или используйте режим инкогнито

### 3. Проверьте сценарии

#### Сценарий 1: Пользователь не авторизован

1. Откройте http://localhost:3000
2. **Ожидание:** Экран "⏳ Загрузка..." → перенаправление на `/auth`
3. Проверьте консоль:
   ```
   ❌ POST /auth/refresh - 401 Unauthorized (только один раз!)
   ```
4. **НЕ должно быть:**
   - Множественных вызовов `/auth/refresh`
   - Перенаправлений на `/dashboard/summary`
   - Бесконечного цикла

#### Сценарий 2: Пользователь авторизован, но не прошел онбординг

1. Войдите в систему
2. **Ожидание:** Автоматическое перенаправление на `/onboarding`
3. Проверьте консоль:
   ```
   ✅ POST /auth/login - 200 OK
   ✅ GET /auth/me - 200 OK
   ```
4. **Ожидание:** Пользователь остается на странице онбординга (не мигает)

#### Сценарий 3: Пользователь авторизован и прошел онбординг

1. Войдите в систему
2. Пройдите онбординг
3. Перезагрузите страницу (F5)
4. **Ожидание:** Экран "⏳ Загрузка..." → главная страница
5. Проверьте консоль:
   ```
   ✅ POST /auth/refresh - 200 OK (только один раз!)
   ✅ GET /auth/me - 200 OK
   ✅ GET /dashboard/summary - 200 OK
   ```

#### Сценарий 4: Истекший refresh token

1. Войдите в систему
2. Удалите cookie `refresh_token` вручную через DevTools
3. Перезагрузите страницу (F5)
4. **Ожидание:** Экран "⏳ Загрузка..." → перенаправление на `/auth`
5. Проверьте консоль:
   ```
   ❌ POST /auth/refresh - 401 Unauthorized (только один раз!)
   ```

## Проверка через DevTools

### 1. Network Tab

1. Откройте DevTools (F12)
2. Перейдите в Network tab
3. Перезагрузите страницу (F5)
4. Проверьте последовательность запросов:
   - Должен быть только **ОДИН** вызов `/auth/refresh`
   - Не должно быть бесконечного цикла
   - Не должно быть вызовов `/dashboard/summary` до авторизации

### 2. Console Tab

1. Откройте Console tab
2. Проверьте отсутствие ошибок:
   - Нет ошибок JavaScript
   - Нет предупреждений о бесконечном цикле
   - Нет ошибок перенаправления

### 3. Application Tab

1. Откройте Application tab
2. Проверьте Cookies:
   - `refresh_token` должна присутствовать после входа
   - `refresh_token` должна отсутствовать после выхода
3. Проверьте Local Storage:
   - Не должно быть лишних данных

## Типичные проблемы

### Проблема: Все еще бесконечный цикл refresh

**Решение:**
1. Убедитесь, что frontend перезапущен (`npm run dev`)
2. Очистите кэш браузера
3. Проверьте, что изменения в `src/api/client.ts` применены
4. Проверьте, что изменения в `src/contexts/AuthContext.tsx` применены

### Проблема: Мигание онбординга

**Решение:**
1. Проверьте, что в `AuthContext` есть проверка `currentPath !== "/onboarding"`
2. Убедитесь, что `sessionRestoredRef` используется
3. Очистите кэш браузера

### Проблема: Перенаправление на /auth вместо /onboarding

**Решение:**
1. Проверьте, что пользователь авторизован (`isAuthenticated = true`)
2. Проверьте, что `user.is_onboarded = false`
3. Проверьте, что текущий путь не `/auth` и не `/register`

## Архитектура защиты

```
┌─────────────────────────────────────────────────────────┐
│                    App Load                              │
└─────────────────────────────────────────────────────────┘
                          ↓
              ┌───────────────────────┐
              │ sessionRestoredRef?   │
              └───────────────────────┘
                    ↓         ↓
                   NO         YES
                    ↓         ↓
          ┌─────────┴──┐  ┌─┴──────────┐
          │ Restore    │  │ Skip       │
          │ Session    │  │ Restore    │
          └────────────┘  └────────────┘
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
          │ Load user  │  │            │
          └────────────┘  └────────────┘
                                 ↓
                    ┌───────────────────────┐
                    │   Check user state    │
                    └───────────────────────┘
                                 ↓
                    ┌───────────────────────┐
                    │ is_onboarded?         │
                    └───────────────────────┘
                    ↓         ↓
                   YES        NO
                    ↓         ↓
          ┌─────────┴──┐  ┌─┴──────────┐
          │ Load       │  │ Redirect   │
          │ Dashboard  │  │ to         │
          └────────────┘  │ /onboarding│
                          └────────────┘

┌─────────────────────────────────────────────────────────┐
│                 401 Error Handling                       │
└─────────────────────────────────────────────────────────┘
                          ↓
              ┌───────────────────────┐
              │ Is refresh request?   │
              └───────────────────────┘
                    ↓         ↓
                   YES        NO
                    ↓         ↓
          ┌─────────┴──┐  ┌─┴──────────┐
          │ Don't      │  │ Dispatch   │
          │ dispatch   │  │ event      │
          └────────────┘  └────────────┘
                                 ↓
                    ┌───────────────────────┐
                    │ isRefreshing?         │
                    └───────────────────────┘
                    ↓         ↓
                   YES        NO
                    ↓         ↓
          ┌─────────┴──┐  ┌─┴──────────┐
          │ Skip       │  │ Set flag   │
          │ refresh    │  │ Refresh    │
          └────────────┘  └────────────┘
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
          │ Update     │  │ Clear state│
          │ tokens     │  │ Redirect   │
          └────────────┘  │ to /auth   │
                          └────────────┘
```

## Статус

✅ Бесконечный цикл refresh исправлен  
✅ Мигание онбординга исправлено  
✅ Множественные вызовы restoreSession исправлены  
✅ Frontend пересобран  
✅ Готово к использованию  

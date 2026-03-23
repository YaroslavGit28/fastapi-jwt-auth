## Архитектурная схема: путь запроса и JWT

Ниже — полный путь обработки запроса в проекте `fastapi-jwt-auth-main` (FastAPI + Bearer + JWT).

### 1) Логин и выдача access token
Запрос: `POST /auth/login`

Ключевые этапы:
1. Клиент отправляет `username` и `password`.
2. FastAPI принимает HTTP-запрос и валидирует тело через Pydantic-модель `LoginRequest`.
3. Роутер вызывает `AuthService.authenticate_user(...)`.
4. `AuthService` обращается к `UserRepository.get_user_by_username(...)`.
5. `verify_password(...)` проверяет пароль через `bcrypt`.
6. При успешной проверке создаётся JWT access token:
   - в payload кладётся `sub` (username)
   - добавляются `iat` и `exp`
   - токен подписывается алгоритмом `HS256` секретом `JWT_SECRET`
7. Роутер возвращает `TokenResponse` с `access_token`, `token_type="bearer"` и `expires_in`.

Если проверка не прошла (пользователь не найден, пароль неверный или `user.disabled=True`), приложение возвращает `401` и заголовок `WWW-Authenticate: Bearer`.

### 2) Защищённый роут /users/me
Запрос: `GET /users/me`

Ключевые этапы:
1. Клиент отправляет token в заголовке `Authorization: Bearer <token>`.
2. Dependency `get_current_user_username` срабатывает через `Depends(...)` в роуте.
3. `HTTPBearer` извлекает токен из заголовка.
4. `decode_access_token(...)` валидирует:
   - подпись
   - срок действия (`exp`)
5. Из payload берётся `sub`, и dependency возвращает `username` в роутер.
6. `UserService.get_user_by_username(...)` формирует `UserResponse`.
7. Роутер отдаёт ответ клиенту.

Если JWT невалидный или истёк (`ExpiredSignatureError` / `JWTError`), dependency поднимает `HTTPException`, и endpoint отвечает `401` c `WWW-Authenticate: Bearer`.

### Mermaid-схема (строго по шагам 1–12)

```mermaid
flowchart TD
  Client[Клиент] -->|1) Запрос /login| Server[FastAPI (сервер)]
  Server -->|2) Принимает HTTP-запрос| RouterLogin[Роутер: /auth/login]
  RouterLogin -->|3) Pydantic-валидация| Validate[LoginRequest (username/password)]
  Validate -->|4) Проверка пользователя| Check[Проверка (AuthService + repo + bcrypt)]
  Check -->|5) Генерация JWT| JWT[JWT (sub + exp + подпись HS256)]
  JWT -->|6) Возврат токена| ClientResp[Ответ API: access_token (TokenResponse)]
  ClientResp -->|7) Запрос /me| Server2[FastAPI (сервер)]
  Server2 -->|8) Token в Authorization header| RouterMe[Роутер: /users/me]
  RouterMe -->|9) Проверка JWT| AuthCheck[Dependency: get_current_user_username + decode_access_token]
  AuthCheck -->|10) Извлечение пользователя из токена| Extract[username из payload.sub]
  Extract -->|11) Выполнение защищённого роутера| Protected[Защищённый обработчик /users/me]
  Protected -->|12) Возврат ответа пользователю| ClientFinal[Ответ API: UserResponse]
```


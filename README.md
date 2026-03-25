# JWT-аутентификация в FastAPI: полный путь запроса от `/auth/login` до `/users/me`

Когда читаешь статьи про JWT, часто остаётся ощущение “ну ладно, токен сгенерировали — а дальше что?”. На практике же самое важное — проследить именно цепочку запроса: где входные данные валидируются, где проверяется пользователь, где добавляются поля в `payload`, и где в итоге security превращает заголовок `Authorization` в конкретного пользователя для защищённого endpoint.

В рамках домашнего задания я разобрал учебный репозиторий `fastapi-jwt-auth` и решил описать свой разбор не как “ещё одно объяснение JWT”, а как архитектурную карту того, как запрос проходит через слои FastAPI: `routers` → `services` → `security` → `repository`. В качестве сценария взял самый показательный путь: получить access token через `POST /auth/login`, а затем использовать его для защищённого `GET /users/me`.

Сразу оговорюсь: проект учебный, repository хранит пользователей в памяти и refresh token в коде не реализован. Но это даже полезнее для понимания: меньше абстракций — легче увидеть механизм.

## Постановка проблемы: “где живёт проверка токена?”

Типичная проблема новичка (и иногда — причина багов в проде) заключается в том, что проверка токена расползается по роутерам: где-то её забыли, где-то сделали иначе, где-то вернули разные ошибки. В этом проекте проверка авторизации оформлена как dependency, а значит её можно одинаково подключать к любым защищённым endpoint.

Для понимания достаточно проследить два точки входа:

1) `POST /auth/login` — здесь приложение принимает `username/password` и выдаёт `access_token`.
2) `GET /users/me` — здесь приложение не знает ничего про JWT “внутри роутера”: оно получает `username` через `Depends(...)`.

## Как работает `POST /auth/login`

Роутер `login` в `app/routers/router.py` объявляет публичный endpoint без токена. Он описывает контракт через Pydantic-схемы и по сути выполняет роль “HTTP-адаптера”: преобразует JSON тела в `LoginRequest`, а затем делегирует в `AuthService`.

Фрагмент логики роутера (ключевые строки):

```python
@auth_router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
)
async def login(request: LoginRequest):
    token_data = auth_service.authenticate_user(request.username, request.password)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(**token_data)
```

Здесь важно не столько то, что возвращается `TokenResponse`, сколько то, что “правило 401” формируется централизованно: если `authenticate_user` вернул `None`, роутер возвращает `401` и подсвечивает клиенту `WWW-Authenticate: Bearer`.

## Где проверяется пароль и собирается JWT

В `app/services/user_service.py` находится `AuthService.authenticate_user`. Именно там происходит:
1) поиск пользователя,
2) проверка пароля через `bcrypt`,
3) проверка флага `disabled`,
4) генерация JWT access token.

Критичный фрагмент сервиса:

```python
user = self.user_repo.get_user_by_username(username)
if not user:
    return None

if not verify_password(password, user.hashed_password):
    return None

if user.disabled:
    return None

access_token = create_access_token(
    data={"sub": user.username},
    expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
)
```

Обратите внимание на поле `sub`: в этом проекте оно хранит `user.username`. Это решение удобно тем, что дальше из токена можно достать имя пользователя без дополнительных таблиц/маппингов.

Пароли реализованы в `app/security/auth.py` через `bcrypt`:

```python
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )
```

## Что внутри JWT: `exp`, `iat` и подпись

После успешной проверки пароля `AuthService` вызывает `create_access_token`. В `create_access_token` формируется payload и добавляются временные метки:
- `iat` (issued at),
- `exp` (expiration time).

Пример из проекта:

```python
to_encode = data.copy()

expire = datetime.now(timezone.utc) + expires_delta

to_encode.update({
    "exp": expire,
    "iat": datetime.now(timezone.utc)
})

encoded_jwt = jwt.encode(
    to_encode,
    settings.JWT_SECRET,
    algorithm=settings.JWT_ALGORITHM
)
```

Технический смысл простой: если токен истёк — сервер не должен позволять использовать его дальше, а проверка должна быть детерминированной. В этом проекте детерминизм достигается за счёт валидации в `decode_access_token`.

## Как работает `GET /users/me`: проверка токена через dependency

Теперь самое интересное с точки зрения архитектуры: защищённый endpoint почти не содержит логики про токен. Он просто объявляет dependency параметром:

```python
async def get_current_user(username: str = Depends(get_current_user_username)):
```

А уже `get_current_user_username` в `app/security/auth.py` делает всю “security магию”: достаёт токен из заголовка `Authorization`, декодирует JWT, валидирует подпись и срок жизни, извлекает `sub`.

Ключевой фрагмент dependency:

```python
token = credentials.credentials
payload = decode_access_token(token)

username: str = payload.get("sub")
if username is None:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
return username
```

Функция `decode_access_token` ловит ошибки `ExpiredSignatureError` и `JWTError` и в обоих случаях возвращает `401` с `WWW-Authenticate: Bearer`:

```python
except ExpiredSignatureError:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="token has expired",
        headers={"WWW-Authenticate": "Bearer"}
    )
except JWTError:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
```

После того как dependency успешно вернула `username`, роутер вызывает `user_service.get_user_by_username(username)` и возвращает `UserResponse`. В результате роутер получает “готового пользователя”, а проверка токена не размазывается по endpoint’ам.

## Pydantic-схемы: валидация входа и формирование ответа

Ещё один плюс архитектуры — “контракт” явно оформлен моделями в `app/repository/models.py`.

Например, вход для логина:

```python
class LoginRequest(BaseModel):
    username: str
    password: str
```

Ответ с токеном:

```python
class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int  # в секундах
```

И ответ для текущего пользователя (без `hashed_password`):

```python
class UserResponse(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    disabled: bool = False
```

Это помогает избежать утечек: даже если в `UserInDB` есть `hashed_password`, наружу его не отдадут, потому что `response_model` описывает другую структуру.

## Схема работы: полный путь запроса

Ниже — архитектурная схема “маршрута запроса”:
<img width="1891" height="5696" alt="567770800-61a1c202-0656-405c-ab7f-e4609f1b00ff" src="https://github.com/user-attachments/assets/b934199b-31ca-443d-b6d6-a07e37bbb282" />


## Выводы: что даёт такая архитектура

Самое ценное, что я вынес из разбора этого проекта: проверка токена встраивается в запрос через dependency injection, а значит security становится “частью пайплайна”, а не ручной припиской в каждом роуте. При добавлении новых защищённых эндпоинтов достаточно подключить ту же dependency `get_current_user_username` — и логика проверки `exp + подпись` будет одинаковой.

Второй полезный момент — простая схема полей в JWT. Использование `sub` и временных `exp/iat` делает токен объяснимым: по сути это подписанное подтверждение “кто пользователь” и “до какого момента токен действует”. В учебном проекте refresh token не добавлен, но фундамент для расширения уже заложен.

Если же вы будете дорабатывать систему под реальные требования, следующий шаг логичный: добавить refresh token, хранение/ротацию ключей, и расширить авторизацию (например, роли/permissions). Но начинать всё равно проще с понятного маршрута запроса, который легко проследить в коде — как в `fastapi-jwt-auth`.

Таким образом, этот разбор — не только про JWT, а про путь запроса и разделение ответственности в FastAPI: роуты решают HTTP, сервисы решают бизнес-логику, `security` инкапсулирует JWT/пароли, а repository отделяет данные от остального приложения.


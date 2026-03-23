## Часть 2. Разбор кода проекта (файлы и логика) — подробный

В этом задании важно не “просто сказать JWT”, а показать, где именно в вашем коде происходит:
1) валидация входных данных,
2) проверка пользователя/пароля,
3) генерация JWT,
4) проверка JWT на защищённых запросах,
5) извлечение пользователя и формирование ответа.

Ниже я пройдусь по ключевым файлам и приведу примеры кода из репозитория `fastapi-jwt-auth-main`.

### `main.py` (подключение роутеров)
`main.py` создаёт `FastAPI`-приложение и регистрирует роутеры:

```python
app.include_router(auth_router)
app.include_router(users_router)
```

То есть фактически “маршруты” `/auth/...` и `/users/...` собираются в одном месте, а их реализация лежит в `app/routers/router.py`.

### `app/routers/router.py` (эндпоинты `/login` и `/users/me`)
Здесь два роутера: один для логина (публичный), второй для “текущего пользователя” (защищённый).

#### `POST /auth/login`
Ключевая идея: роутер получает валидированный Pydantic-запрос, а затем делегирует работу в `AuthService`.

Фрагмент регистратора эндпоинта:

```python
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

@auth_router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
)
async def login(request: LoginRequest):
```

Дальше — реальная логика:

```python
token_data = auth_service.authenticate_user(request.username, request.password)
if not token_data:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )
return TokenResponse(**token_data)
```

Что здесь важно для понимания “полного пути запроса”:
1) тело запроса проверяется Pydantic-моделью `LoginRequest`,
2) при неуспехе возвращается `401` и добавляется заголовок `WWW-Authenticate: Bearer`,
3) при успехе ответ отдаётся как `TokenResponse` (access token + metadata).

Пример запроса:
```json
{"username": "admin", "password": "admin123"}
```

Пример ответа (по форме):
```json
{"access_token": "...", "token_type": "bearer", "expires_in": 1800}
```

#### `GET /users/me` (защищённый endpoint)
Здесь токен проверяется не “внутри функции роутера”, а через dependency injection.

Фрагмент:
```python
@users_router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def get_current_user(username: str = Depends(get_current_user_username)):
```

И дальше роутер использует полученный `username`:

```python
user = user_service.get_user_by_username(username)
if not user:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )
return user
```

То есть `router.py` не знает деталей JWT — они скрыты в `get_current_user_username(...)` в `app/security/auth.py`.

### `app/repository/models.py` (Pydantic схемы: вход и выход)
Pydantic тут отвечает за валидацию входа и формат ответа.

Ключевые модели:

```python
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int  # в секундах

class UserResponse(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    disabled: bool = False
```

Отдельно: `hashed_password` лежит в `User`/`UserInDB`, но `UserResponse` его не содержит, поэтому пароль не утечёт наружу.

### `app/services/user_service.py` (бизнес-логика: проверка и генерация токена)
В проекте бизнес-логика разделена на `AuthService` и `UserService`.

#### `AuthService.authenticate_user(...)`
Этот метод — сердце логина:

```python
user = self.user_repo.get_user_by_username(username)
if not user:
    return None

if not verify_password(password, user.hashed_password):
    return None

if user.disabled:
    return None

access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
access_token = create_access_token(
    data={"sub": user.username},
    expires_delta=access_token_expires
)

return {
    "access_token": access_token,
    "token_type": "bearer",
    "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
}
```

Обратите внимание на поле `sub`: в токене хранится `sub = user.username`.
Это напрямую используется дальше в dependency для защищённых роутов.

#### `UserService.get_user_by_username(...)`
Здесь формируется ответ без пароля:

```python
user = self.user_repo.get_user_by_username(username)
if not user:
    return None

if user.disabled:
    return None

return UserResponse(
    username=user.username,
    email=user.email,
    full_name=user.full_name,
    disabled=user.disabled
)
```

### `app/security/auth.py` (пароли, JWT, и dependency `Depends(...)`)
Этот файл связывает JWT и защиту эндпоинтов.

#### Пароли (bcrypt)
Используется `bcrypt`:

```python
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )
```

И хеширование (используется при инициализации in-memory пользователей):
```python
def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")
```

#### Генерация JWT (`create_access_token`)
JWT создаётся через `python-jose`, и в него добавляются `exp` и `iat`:

```python
to_encode = data.copy()

if expires_delta:
    expire = datetime.now(timezone.utc) + expires_delta
else:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

to_encode.update({
    "exp": expire,
    "iat": datetime.now(timezone.utc)
})

encoded_jwt = jwt.encode(
    to_encode,
    settings.JWT_SECRET,
    algorithm=settings.JWT_ALGORITHM
)
return encoded_jwt
```

То есть срок жизни токена задаётся через `exp`, а проверка делается при декодировании.

#### Проверка JWT (`decode_access_token`)
Если токен истёк или подпись некорректна — возвращается `401`:

```python
payload = jwt.decode(
    token,
    settings.JWT_SECRET,
    algorithms=settings.JWT_ALGORITHM
)
return payload
```

Ошибки:
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

#### Dependency `get_current_user_username(...)`
Это именно тот кусок, который “подключается” в `GET /users/me` через `Depends(...)`.

```python
credentials: HTTPAuthorizationCredentials = Depends(security_scheme)
token = credentials.credentials

payload = decode_access_token(token)

username: str = payload.get("sub")
if username is None:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )

return username
```

Итог: роутер получает уже готовое значение `username`, а проверка токена скрыта в dependency.

### `app/repository/user_repository.py` (источник данных пользователей)
В этом учебном проекте users хранятся в памяти:

```python
self._users: dict[str, UserInDB] = {
  "admin": UserInDB(
      username="admin",
      email="admin@example.com",
      full_name="Maxim_Admin",
      hashed_password=get_password_hash("admin123"),
      disabled=False
  ),
  "user": UserInDB(
      username="user",
      email="user@example.com",
      full_name="Regular User",
      hashed_password=get_password_hash("user123"),
      disabled=False
  )
}
```

Метод, который нужен для логина и для `/users/me`:
```python
def get_user_by_username(self, username: str) -> Optional[UserInDB]:
    return self._users.get(username)
```

### `app/configs/settings.py` (настройки JWT)
Ключевые поля:

```python
JWT_ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
```

Секрет `JWT_SECRET` берётся из окружения/`.env` через `BaseSettings`.
Он используется и в `create_access_token`, и в `decode_access_token`.

### Что “видит” клиент (кратко: статус-коды и ответы)
При `POST /auth/login`:
- успех: `200` + `TokenResponse`
- неуспех: `401`, `detail="Incorrect username or password"`, `WWW-Authenticate: Bearer`

При `GET /users/me`:
- успех: `200` + `UserResponse`
- неверный/просроченный токен: `401` (в зависимости от ошибки в `decode_access_token`)
- пользователя нет: `404 User not found`


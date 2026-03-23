from typing import Optional
from pydantic import BaseModel, EmailStr

class User(BaseModel):
    """
    Модель пользователя.
    
    Attributes:
        username: Уникальное имя пользователя
        email: Email пользователя
        full_name: Полное имя пользователя
        hashed_password: Хешированный пароль (никогда не возвращается в API)
        disabled: Флаг блокировки пользователя
    """

    username: str
    email: EmailStr
    full_name: Optional[str] = None 
    hashed_password: str 
    disabled: bool = False


class UserInDB(User):
    """
    Модель пользователя для базы данных 
    Наследуются все поля из User
    """
    pass

class UserResponse(BaseModel):
    """
    Модель пользователя для ответа API.
    Не содержит конфиденциальных данных (пароль).
    """

    username: str
    email: EmailStr
    full_name: Optional[str] = None 
    disabled: bool = False


class LoginRequest(BaseModel):
    """Запрос на вход в систему."""
    username: str
    password: str

class TokenResponse(BaseModel):
    """Ответ с токеном."""
    access_token: str
    token_type: str
    expires_in: int  # в секундах
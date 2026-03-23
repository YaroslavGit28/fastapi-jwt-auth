import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, ExpiredSignatureError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.configs import settings

security_scheme = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет соответствие открытого пароля хешу.
    
    Args:
        plain_password: Пароль в открытом виде
        hashed_password: Хешированный пароль
        
    Returns:
        True если пароль соответствует хешу
    """
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    """
    Хеширует пароль с помощью bcrypt.
    
    Args:
        password: Пароль в открытом виде
        
    Returns:
        Хешированный пароль
    """

    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")



def create_access_token(data: dict, expires_delta: Optional[timedelta]=None) -> str:
    """
    Создает JWT access token.
    
    Токен содержит:
    - sub: subject (обычно user_id или username)
    - exp: expiration time
    - iat: issued at time
    
    Args:
        data: Данные для включения в токен (должны содержать "sub")
        expires_delta: Время жизни токена (по умолчанию из настроек)
        
    Returns:
        Закодированный JWT токен
    """

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


def decode_access_token(token: str) -> dict:
    """
    Декодирует и проверяет JWT токен.
    
    Проверяет:
    - Корректность подписи
    - Срок действия (exp)
    
    Args:
        token: JWT токен
        
    Returns:
        Payload токена
        
    Raises:
        HTTPException: Если токен невалиден или истек
    """


    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=settings.JWT_ALGORITHM
        )
        return payload 
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


def get_current_user_username(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)) -> str:
    """
    FastAPI dependency для извлечения текущего пользователя из токена.
    
    Эта функция:
    1. Извлекает токен из заголовка Authorization: Bearer <token>
    2. Проверяет токен
    3. Извлекает username из поля "sub"
    
    Роутеры не знают деталей проверки токена - это инкапсулировано здесь.
    
    Args:
        credentials: Автоматически извлекается FastAPI из заголовка
        
    Returns:
        Username текущего пользователя
    Raises:
        HTTPException 401: Если токен отсутствует, невалиден или истек
    """

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except HTTPException:
        # propagate HTTPExceptions raised during decoding (expired/invalid token)
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return username
        

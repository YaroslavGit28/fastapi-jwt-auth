from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

from app.services import auth_service, user_service
from app.repository import UserResponse, LoginRequest, TokenResponse
from app.security import get_current_user_username

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

@auth_router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Успешная аутентификация"},
        401: {"description": "Неверный логин или пароль"},
    }
)
async def login(request: LoginRequest):
    """
    Аутентификация пользователя.
    
    Публичный эндпоинт (не требует токена).
    
    Принимает:
    - username: имя пользователя
    - password: пароль
    
    Возвращает:
    - access_token: JWT токен для последующих запросов
    - token_type: "bearer"
    - expires_in: время жизни токена в секундах
    
    Статусы:
    - 200 OK: успешная аутентификация
    - 401 Unauthorized: неверные учетные данные
    """
    
    token_data = auth_service.authenticate_user(request.username, request.password)
    if not token_data:
        # Возвращаем 401 если аутентификация не удалась
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return TokenResponse(**token_data)


users_router = APIRouter(prefix="/users", tags=["Users"])

@users_router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Данные текущего пользователя"},
        401: {"description": "Нет токена или токен невалиден"},
        404: {"description": "Пользователь не найден"},
    }
)
async def get_current_user(username: str = Depends(get_current_user_username)):
    """
    Получить данные текущего пользователя.
    
    Защищенный эндпоинт (требует Bearer токен).
    
    Токен должен быть передан в заголовке:
    Authorization: Bearer <token>
    
    Возвращает данные пользователя без конфиденциальной информации.
    
    Статусы:
    - 200 OK: данные пользователя
    - 401 Unauthorized: нет токена, токен невалиден или истек
    - 404 Not Found: пользователь не найден (удален или заблокирован)
    
    Примечание:
    Роутер не проверяет токен вручную - это делается через dependency.
    Роутер не знает деталей токена - он получает только username.
    """
    # Получаем данные пользователя через service
    user = user_service.get_user_by_username(username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user
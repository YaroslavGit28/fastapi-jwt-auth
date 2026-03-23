from os import access
from typing import Optional
from datetime import timedelta

from app.repository import user_repository, UserResponse
from app.configs import settings
from app.security import verify_password, create_access_token


class AuthService:
    """
    Service для бизнес-логики аутентификации.
    
    Принципы:
    - Service содержит бизнес-логику
    - Использует repository для доступа к данным
    - Использует security для работы с токенами
    - Не знает об HTTP (роутеры преобразуют HTTP в вызовы service)
    """


    def __init__(self):
        self.user_repo = user_repository

    def authenticate_user(self, username: str, password: str) -> Optional[dict]:
        """
        Аутентифицирует пользователя по логину и паролю.
        
        Бизнес-логика:
        1. Проверяет существование пользователя
        2. Проверяет пароль
        3. Проверяет что пользователь не заблокирован
        4. Генерирует access token
        
        Args:
            username: Имя пользователя
            password: Пароль
            
        Returns:
            Словарь с токеном и информацией или None если аутентификация не удалась
        """

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
    

class UserService:
    """
    Service для бизнес-логики работы с пользователями.
    """
    
    def __init__(self):
        self.user_repo = user_repository
    
    def get_user_by_username(self, username: str) -> Optional[UserResponse]:
        """
        Получает данные пользователя (без конфиденциальной информации).
        
        Args:
            username: Имя пользователя
            
        Returns:
            Данные пользователя или None
        """
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
    

auth_service = AuthService()
user_service = UserService()
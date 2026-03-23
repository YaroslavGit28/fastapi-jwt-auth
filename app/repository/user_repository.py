from typing import Optional 
from app.repository.models import UserInDB
from app.security.auth import get_password_hash


class UserRepository:
    """
    Repository для работы с пользователями.
    
    Принципы:
    - Repository отвечает только за данные
    - Не содержит бизнес-логику
    - Изолирует остальные слои от деталей хранения
    """


    def __init__(self):
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
    
    def get_user_by_username(self, username: str) -> Optional[UserInDB]:
        """
        Получает пользователя по имени.
        
        Args:
            username: Имя пользователя
            
        Returns:
            Объект пользователя или None если не найден
        """

        return self._users.get(username)
    
    def create_user(self, user: UserInDB) -> UserInDB:
        """
        Создает нового пользователя.
        
        Args:
            user: Данные пользователя
            
        Returns:
            Созданный пользователь
            
        Raises:
            ValueError: Если пользователь с таким username уже существует
        """
        if user.username in self._users:
            raise ValueError(f"User {user.username} already exists")
        
        self._users[user.username] = user 
        return user 
    
    def user_exists(self, username: str) -> bool:
        """
        Проверяет существование пользователя.
        
        Args:
            username: Имя пользователя
            
        Returns:
            True если пользователь существует
        """
        return username in self._users

   
user_repository = UserRepository()
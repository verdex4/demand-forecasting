from pydantic import BaseModel


# СХЕМЫ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ (Users)
class UserBase(BaseModel):
    """Базовая схема для пользователя."""
    pass

class UserCreate(UserBase):
    """Схема для создания нового пользователя (входные данные)."""
    email: str
    password: str

class UserCreateOut(UserBase):
    """Схема для вывода результата создания пользователя."""
    user_id: int
    jwt: str

class UserLogin(UserBase):
    """Схема для входа пользователя (входные данные)."""
    email: str
    password: str

class UserLoginOut(UserBase):
    """Схема для вывода результата входа пользователя."""
    user_id: int
    jwt: str
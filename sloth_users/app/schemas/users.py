from uuid import UUID, uuid4
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field

from app.schemas.utils import PhoneNumber


class BaseUser(BaseModel):
    """Базовая схема юзера"""
    username: str = Field(
        description='username'
    )
    email: EmailStr = Field(
        description='email пользователя'
    )
    hashed_pass: str = Field(
        description='хэшированный пароль',
    )
    phone: PhoneNumber = Field(
        description='телефон пользователя'
    )
    is_verified: bool = Field(
        description='подтвержден ли пользователь',
        default=False
    )
    rating: Optional[Decimal] = Field(
        description='рейтинг пользователя',
        default=None,
        ge=1.00,
        le=5.00,
        decimal_places=2
    )
    role: str = Field(
        description='роль пользователя'
    )
    created_at: Optional[datetime] = Field(
        description='Время создания записи',
        default_factory=datetime.now
    )
    updated_at: Optional[datetime] = Field(
        description='Время обновления записи',
        default_factory=datetime.now
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "_id": "c9bf9e57-1685-4c89-bafb-ff5af830be8a",
                "username": "john_doe",
                "email": "john@example.com",
                "hashed_pass": "hashedpassword123",
                "phone": "+123456789",
                "is_verified": True,
                "rating": 4.75,
                "role": "admin",
                "created_at": "2024-08-31T12:34:56",
                "updated_at": "2024-08-31T12:34:56"
            }
        }
    }


class UserCreate(BaseUser):
    """Схема создания нового пользователя"""
    

class UserCreateResponse(BaseModel):
    """Схема ответа на создание нового пользователя"""
    id: UUID = Field(
        description='Уникальный идентификатор пользователя'
    )
    username: str = Field(
        description='Имя пользователя'
    )
    email: EmailStr = Field(
        description='Email пользователя'
    )
    phone: str = Field(
        description='Телефон пользователя'
    )
    is_verified: bool = Field(
        description='Подтвержден ли пользователь',
        default=False
    )
    rating: Optional[Decimal] = Field(
        description='Рейтинг пользователя',
        default=None,
        ge=1.00,
        le=5.00,
        decimal_places=2
    )
    role: str = Field(
        description='Роль пользователя'
    )
    created_at: Optional[datetime] = Field(
        description='Время создания записи',
        default_factory=datetime.now
    )
    updated_at: Optional[datetime] = Field(
        description='Время обновления записи',
        default_factory=datetime.now
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "c9bf9e57-1685-4c89-bafb-ff5af830be8a",
                "username": "john_doe",
                "email": "john@example.com",
                "phone": "+123456789",
                "is_verified": True,
                "rating": 4.75,
                "role": "admin",
                "created_at": "2024-08-31T12:34:56",
                "updated_at": "2024-08-31T12:34:56"
            }
        }
    }



class UserUpdate(BaseUser):
    """Схема обновления пользователя"""
    pass


class GetUserResponse(UserCreateResponse):
    """Схема получения одного пользователя"""
    pass


class GetAllUsersListResponse(BaseModel):
    """Схема получения списка всех пользователей"""
    users: List[GetUserResponse] = Field(
        description='список пользователей'
    )

    class Config:
        json_schema_extra = {
            "example": {
                "users": [
                    {
                        "_id": "c9bf9e57-1685-4c89-bafb-ff5af830be8a",
                        "username": "john_doe",
                        "email": "john@example.com",
                        "hashed_pass": "hashedpassword123",
                        "phone": "+123456789",
                        "is_verified": True,
                        "rating": 4.75,
                        "role": "admin",
                        "created_at": "2024-08-31T12:34:56",
                        "updated_at": "2024-08-31T12:34:56"
                    },
                    {
                        "_id": "d7fda6f1-16ae-4e7f-bb9b-df5e76b9b3ea",
                        "username": "jane_doe",
                        "email": "jane@example.com",
                        "hashed_pass": "hashedpassword456",
                        "phone": "+987654321",
                        "is_verified": False,
                        "rating": 4.50,
                        "role": "user",
                        "created_at": "2024-09-01T14:20:30",
                        "updated_at": "2024-09-01T14:20:30"
                    }
                ]
            }
        }
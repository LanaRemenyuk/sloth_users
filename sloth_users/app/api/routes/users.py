import asyncpg
import redis
import requests
from uuid import UUID
from fastapi import APIRouter, Depends, Request, HTTPException, status, Body
from app.db.functions import execute_get_all_users, execute_get_user_by_id, execute_delete_user
from app.db.procedures import execute_create_user, execute_update_user
from app.db import get_db
from app.api.utils.pass_utils import hash_password
from app.api.routes.dependencies import get_current_user, token_required, handle_user_creation, handle_user_update
from app.core.config import settings
from app.schemas.users import UserCreate, UserCreateResponse, UserUpdate, GetAllUsersListResponse, GetUserResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix=f'/api/v1/{settings.service_name}'
)

redis = redis.from_url(f"redis://{settings.redis_host}:{settings.redis_port}", decode_responses=True)

@router.post('', status_code=status.HTTP_201_CREATED, response_model=UserCreateResponse)
async def create_user(user: UserCreate, conn: asyncpg.Connection = Depends(get_db)) -> UserCreateResponse:
    try:
        user_response = await handle_user_creation(conn, user)
        auth_response = requests.post(f'{settings.auth_service_url}/login', json={"user_id": str(user_response.id)})
        if auth_response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to create tokens in auth service")
        
        token_data = auth_response.json()

        return UserCreateResponse(
            id=user_response.id,
            username=user_response.username, 
            email=user_response.email,
            phone=user_response.phone,
            role=user_response.role,
            access_token=token_data['access_token'],
            token_type=token_data['token_type']
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/{user_id}', status_code=status.HTTP_200_OK, response_model=GetUserResponse)
@token_required
async def get_user(user_id: UUID, request: Request, conn: asyncpg.Connection = Depends(get_db),
current_user: UUID = Depends(get_current_user),
)  -> GetUserResponse:
    user = await execute_get_user_by_id(conn, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
    return GetUserResponse(**user)

@router.patch('/{user_id}', status_code=status.HTTP_200_OK)
@token_required
async def update_user(user_id: UUID, request: Request, conn: asyncpg.Connection = Depends(get_db),
current_user: UUID = Depends(get_current_user)) -> dict:
    user_data = await request.json()
    try:
        updated_user = await handle_user_update(conn, user_id, user_data)
        return updated_user
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))  

@router.delete('/{user_id}', status_code=status.HTTP_204_NO_CONTENT)
@token_required
async def delete_user(user_id: UUID, request: Request, conn: asyncpg.Connection = Depends(get_db),
current_user: UUID = Depends(get_current_user)) -> None:
    try:
        await execute_delete_user(conn, user_id)
    except HTTPException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


@router.post('/verify_code/{user_id}/', status_code=status.HTTP_200_OK)
@token_required
async def verify_code(
    user_id: UUID, 
    request: Request,
    verification_code: str, 
    conn: asyncpg.Connection = Depends(get_db),
    current_user: UUID = Depends(get_current_user)
) -> dict:
    """
    Эндпоинт для верификации 6-значного кода, отправленного на почту.
    """
    user = await conn.fetchrow('SELECT email FROM users WHERE id = $1', user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Пользователь не найден"
        )
    email = user['email']

    # Получаем код из Redis по ключу email
    redis_key = f"verification_code:{email}"
    stored_code = redis.get(redis_key)  # Use synchronous get

    if stored_code == verification_code:
        await conn.execute('UPDATE users SET is_verified = TRUE WHERE id = $1', user_id)

        redis.delete(redis_key)

        return {"message": "Email успешно подтвержден", "is_verified": True}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Коды верификации не совпадают "
        )
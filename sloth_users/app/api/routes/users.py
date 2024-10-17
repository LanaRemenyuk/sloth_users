import asyncpg
import redis
from uuid import UUID
from fastapi import APIRouter, Depends, Request, HTTPException, status
from app.db.functions import execute_get_all_users, execute_get_user_by_id, execute_delete_user
from app.db.procedures import execute_create_user, execute_update_user
from app.db import get_db
from app.api.utils.pass_utils import hash_password
from app.core.config import settings
from app.schemas.users import UserCreate, UserCreateResponse, UserUpdate, GetAllUsersListResponse, GetUserResponse

router = APIRouter(
    prefix=f'/api/v1/{settings.service_name}'
)

redis = redis.from_url(f"redis://{settings.redis_host}:{settings.redis_port}", decode_responses=True)

async def handle_user_creation(conn: asyncpg.Connection, user: UserCreate) -> UserCreateResponse:
    hashed_password = hash_password(user.hashed_pass)
    
    user_id = await execute_create_user(
        conn=conn,
        username=user.username,
        email=user.email,
        hashed_pass=hashed_password,
        phone=user.phone,
        is_verified=user.is_verified,
        rating=user.rating,
        role=user.role
    )
    return UserCreateResponse(
        id=user_id,
        username=user.username,
        email=user.email,
        phone=user.phone,
        is_verified=user.is_verified,
        rating=user.rating,
        role=user.role
    )

async def handle_user_update(conn: asyncpg.Connection, user_id: UUID, user_data: dict) -> dict:
    
    existing_user = await execute_get_user_by_id(conn, user_id)
    if not existing_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
    
    new_password = user_data.get('hashed_pass')
    if new_password:
        hashed_password = hash_password(new_password)
    else:
        hashed_password = existing_user['hashed_pass']
    
    await execute_update_user(
        conn=conn,
        user_id=user_id,
        username=user_data.get('username', existing_user['username']),
        email=user_data.get('email', existing_user['email']),
        hashed_pass=hashed_password,
        phone=user_data.get('phone', existing_user['phone']),
        is_verified=user_data.get('is_verified', existing_user['is_verified']),
        rating=user_data.get('rating', existing_user['rating']),
        role=user_data.get('role', existing_user['role'])
    )
    
    updated_user = await execute_get_user_by_id(conn, user_id)

    return {
        'id': updated_user['id'],
        'username': updated_user['username'],
        'email': updated_user['email'],
        'phone': updated_user['phone'],
        'is_verified': updated_user['is_verified'],
        'rating': updated_user['rating'],
        'role': updated_user['role']
    }


@router.post('', status_code=status.HTTP_201_CREATED, response_model=UserCreateResponse)
async def create_user(user: UserCreate, conn: asyncpg.Connection = Depends(get_db)) -> UserCreateResponse:
    try:
        return await handle_user_creation(conn, user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get('', status_code=status.HTTP_200_OK, response_model=GetAllUsersListResponse)
async def get_all_users(conn: asyncpg.Connection = Depends(get_db)) -> GetAllUsersListResponse:
    try:
        users = await execute_get_all_users(conn)
        return GetAllUsersListResponse(users=[GetUserResponse(**user) for user in users])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/{user_id}', status_code=status.HTTP_200_OK, response_model=GetUserResponse)
async def get_user(user_id: UUID, conn: asyncpg.Connection = Depends(get_db)) -> GetUserResponse:
    user = await execute_get_user_by_id(conn, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
    return GetUserResponse(**user)

@router.patch('/{user_id}', status_code=status.HTTP_200_OK)
async def update_user(user_id: UUID, request: Request, conn: asyncpg.Connection = Depends(get_db)) -> dict:
    user_data = await request.json()
    try:
        updated_user = await handle_user_update(conn, user_id, user_data)
        return updated_user
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))  

@router.delete('/{user_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: UUID, conn: asyncpg.Connection = Depends(get_db)) -> None:
    try:
        await execute_delete_user(conn, user_id)
    except HTTPException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


@router.post('/verify_code/{user_id}/', status_code=status.HTTP_200_OK)
async def verify_code(
    user_id: str, 
    verification_code: str, 
    conn: asyncpg.Connection = Depends(get_db)
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
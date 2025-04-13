import asyncpg
import bcrypt
import httpx
import redis
import requests
from uuid import UUID
from fastapi import APIRouter, Depends, Request, HTTPException, status, Body
from app.db.functions import execute_get_all_users, execute_get_user_by_id, execute_delete_user
from app.db.procedures import execute_create_user, execute_update_user
from app.db import get_db
from app.api.utils.pass_utils import hash_password, verify_password_reset_token
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
async def update_user(user_id: UUID, request: Request, conn: asyncpg.Connection = Depends(get_db)) -> dict:
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


@router.post('/reset_password', status_code=status.HTTP_200_OK)
async def reset_password(
    email: str = Body(...), 
    new_password: str = Body(...),
    conn: asyncpg.Connection = Depends(get_db)
):
    """Эндпоинт для установки нового пароля после сброса."""
    stored_token = redis.get(f"password_reset_token:{email}")
    
    if not stored_token:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    try:
        user_id = verify_password_reset_token(stored_token)
    except HTTPException:
        raise HTTPException(status_code=400, detail="Invalid token")

    hashed_password = hash_password(new_password)
    
    previous_passwords = await conn.fetch(
        """
        SELECT hashed_pass, created_at
        FROM passwords
        WHERE user_id = $1
        """,
        user_id
    )
    for record in previous_passwords:
        old_hashed_password = record['hashed_pass']
        created_at = record['created_at']

        if bcrypt.checkpw(new_password.encode('utf-8'), old_hashed_password.encode('utf-8')):
            raise HTTPException(
                status_code=400,
                detail=f"Данный пароль уже создавался {created_at.strftime('%Y-%m-%d %H:%M:%S')}. Пожалуйста, введите другой пароль."
            )

    await conn.execute(
        """
        INSERT INTO passwords (user_id, hashed_pass, created_at)
        VALUES ($1, $2, NOW())
        """,
        user_id, hashed_password
    )

    return {"message": "Пароль успешно изменен"}

@router.post('/request_password_reset', status_code=status.HTTP_200_OK)
async def request_password_reset(
    email: str = Body(...), 
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Эндпоинт для проверки существования email в users и запроса сброса пароля в auth.
    """
    user = await conn.fetchrow("SELECT id FROM users WHERE email = $1", email)
    
    if not user:
        return {"message": "Данный email не зарегистрирован"}

    auth_url = f"{settings.auth_service_url}/send_password_reset_link?email={email}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(auth_url)
            response.raise_for_status()

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Ошибка при обращении к auth сервису: {e.response.text}"
        )
    
    return {"message": "Ссылка на сброс пароля направлена на указанный email"}

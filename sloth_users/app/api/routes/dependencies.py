import asyncpg
import httpx
from functools import wraps
from uuid import UUID
from fastapi import Depends, HTTPException, Request, Body, status
from typing import Optional
from app.api.utils.pass_utils import hash_password
from app.db.functions import execute_get_user_by_id
from app.db.procedures import execute_create_user, execute_update_user
from app.core.config import settings
from app.schemas.users import UserCreate, UserCreateResponse


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
        'id': user_id,
        'username': updated_user['username'],
        'email': updated_user['email'],
        'phone': updated_user['phone'],
        'is_verified': updated_user['is_verified'],
        'rating': updated_user['rating'],
        'role': updated_user['role']
    }

async def get_current_user(request: Request):
    """Проверка аутентификации через обращение к сервису auth"""
    token = request.headers.get('Authorization')
    if not token or not token.startswith('Bearer'):
        raise HTTPException(status_code=401, detail='Missing or invalid token')

    token = token.split(' ')[1]

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f'{settings.auth_service_url}/verify_token', json={'token': token})
            if response.status_code == 200:
                token_data = response.json()
                return token_data['user_id']
            else:
                token_data = response.json()
                print(token_data)
                raise HTTPException(status_code=response.status_code, detail='Invalid token')
        except httpx.RequestError:
            raise HTTPException(status_code=500, detail='Auth service is unavailable')

async def validate_and_refresh_token(
    request: Request
):
    authorization_header = request.headers.get("Authorization")
    if not authorization_header or not authorization_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid access token")
    
    access_token = authorization_header.split(" ")[1]

    body = await request.json()
    refresh_token: Optional[str] = body.get("refresh_token")

    async with httpx.AsyncClient() as client:
        response = await client.post(f'{settings.auth_service_url}/verify_token', json={"token": access_token})

    if response.status_code == 401:
        if refresh_token:
            refresh_response = await client.post(f'{settings.auth_service_url}/refresh_token', json={"refresh_token": refresh_token})
            if refresh_response.status_code == 200:
                new_access_token = refresh_response.json().get('access_token')
                return {
                    'access_token': new_access_token,
                    'token_type': 'bearer',
                    'message': 'Access token refreshed successfully'
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail='Refresh token is invalid or expired'
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Access token expired'
            )
    elif response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid access token'
        )
    
    return {
        'message': 'Access token is valid',
        'token_type': 'bearer'
    }

def token_required(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request: Request = kwargs.get('request') or args[0]
        authorization_header = request.headers.get("Authorization")
        
        if not authorization_header or not authorization_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid access token")

        access_token = authorization_header.split(" ")[1]

        try:
            body = await request.json()
            refresh_token = body.get("refresh_token")
        except Exception:
            refresh_token = None

        async with httpx.AsyncClient() as client:
            if refresh_token:
                response = await client.post(
                    f'{settings.auth_service_url}/refresh_token',
                    json={"refresh_token": refresh_token},
                    headers={"Authorization": f"Bearer {access_token}"}
                )
            else:
                response = await client.post(
                    f'{settings.auth_service_url}/verify_token',
                    json={"token": access_token}
                )

            if response.status_code == 200:
                return await func(*args, **kwargs)
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)

    return wrapper

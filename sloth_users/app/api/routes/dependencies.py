import httpx
from functools import wraps
from uuid import UUID
from fastapi import Depends, HTTPException, Request, Body
from typing import Optional
from app.core.config import settings


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


from fastapi import HTTPException, Request, status
import httpx
from typing import Optional


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

        body = await request.json()
        refresh_token = body.get("refresh_token")

        async with httpx.AsyncClient() as client:
            response = await client.post(f'{settings.auth_service_url}/validate_and_refresh_token', json={
                "refresh_token": refresh_token
            }, headers={"Authorization": f"Bearer {access_token}"})

            if response.status_code == 200:
                return await func(*args, **kwargs)
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)

    return wrapper

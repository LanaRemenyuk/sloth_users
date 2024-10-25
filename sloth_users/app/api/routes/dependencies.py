import httpx
from uuid import UUID
from fastapi import Depends, HTTPException, Request
from app.core.config import settings

AUTH_SERVICE_URL = f"http://auth:8080/api/v1/auth/verify_token"

async def get_current_user(request: Request):
    """Проверка аутентификации через обращение к сервису auth"""
    token = request.headers.get('Authorization')
    if not token or not token.startswith('Bearer'):
        raise HTTPException(status_code=401, detail='Missing or invalid token')

    token = token.split(' ')[1]

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(AUTH_SERVICE_URL, params={'token': token})
            if response.status_code == 200:
                token_data = response.json()
                print(token_data['user_id'])
                return token_data['user_id']
            else:
                token_data = response.json()
                print(token_data)
                raise HTTPException(status_code=response.status_code, detail='Invalid token')
        except httpx.RequestError:
            raise HTTPException(status_code=500, detail='Auth service is unavailable')

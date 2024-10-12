import asyncpg
from typing import AsyncGenerator, Optional

from app.core.config import settings

DATABASE_URL = settings.postgres_url

connection: Optional[asyncpg.Connection] = None

async def lifespan(app) -> AsyncGenerator:
    """Функция инициализации контекстного менеджера жизненного цикла для соединения с бд"""
    global connection
    if connection is None:
        connection = await asyncpg.connect(str(DATABASE_URL))
        print('Соединение с базой данных установлено')
    yield
    if connection is not None:
        await connection.close()
        print('Соединение с базой данных закрыто')

async def get_db():
    """Dependency для получения соединения с бд"""
    global connection
    if connection is None:
        connection = await asyncpg.connect(DATABASE_URL)
    yield connection

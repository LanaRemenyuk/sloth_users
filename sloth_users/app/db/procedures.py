import asyncpg
from typing import Optional
from uuid import UUID

async def execute_user_procedure(
    conn: asyncpg.Connection,
    procedure_name: str,
    *params
) -> None:
    placeholders = ", ".join([f"${i+1}" for i in range(len(params))])
    sql = f"CALL {procedure_name}({placeholders})"
    await conn.execute(sql, *params)

async def execute_create_user(
    conn: asyncpg.Connection,
    username: str,
    email: str,
    hashed_pass: str,
    phone: str,
    is_verified: bool,
    rating: float,
    role: str
) -> UUID:
    user_id = await conn.fetchval(
        """
        CALL create_user_procedure($1, $2, $3, $4, $5, $6, $7, NULL)
        """,
        username, email, hashed_pass, phone, is_verified, rating, role
    )

    return user_id


async def execute_update_user(conn: asyncpg.Connection, user_id: UUID, **kwargs) -> None:
    params = [
        user_id,                     # UUID пользователя
        kwargs.get('username'),      # Новый username или None
        kwargs.get('email'),         # Новый email или None
        kwargs.get('phone'),         # Новый phone или None
        kwargs.get('is_verified'),   # Новый is_verified или None
        kwargs.get('rating'),        # Новый rating или None
        kwargs.get('role'),          # Новый role или None
        kwargs.get('hashed_pass')    # Новый hashed_pass или None
    ]
    await execute_user_procedure(conn, 'update_user_procedure', *params)


async def log_request(conn: asyncpg.Connection, **kwargs) -> None:
    await execute_user_procedure(conn, 'log_request_procedure', *kwargs.values())
import asyncpg
from typing import Optional
from uuid import UUID

import logging

# Configure the logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

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
    if not isinstance(user_id, UUID):
        logger.error(f"Invalid user_id: {user_id}. It must be a valid UUID.")
        raise ValueError("user_id must be a valid UUID")
    params = [
        user_id,                     # UUID пользователя
        kwargs.get('username'),      # Новый username или None
        kwargs.get('email'),         # Новый email или None
        kwargs.get('phone'),         # Новый phone или None
        kwargs.get('is_verified'),    # Новый is_verified или None
        kwargs.get('rating'),        # Новый rating или None
        kwargs.get('role'),          # Новый role или None
        kwargs.get('hashed_pass')    # Новый hashed_pass или None
    ]
    
    # Log the parameters being passed
    logger.info(f"Preparing to call 'update_user_procedure' with params: {params}")
    
    try:
        # Call the stored procedure
        await execute_user_procedure(conn, 'update_user_procedure', *params)
        
        # Log successful execution
        logger.info("Successfully executed 'update_user_procedure'")
    except Exception as e:
        # Log any exceptions encountered
        logger.error(f"Error executing 'update_user_procedure' :{e}")
        raise  # Re-raise the exception to handle it upstream

async def log_request(conn: asyncpg.Connection, **kwargs) -> None:
    await execute_user_procedure(conn, 'log_request_procedure', *kwargs.values())
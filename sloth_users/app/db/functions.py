import asyncpg
from uuid import UUID
from typing import List, Dict, Optional
from fastapi import HTTPException, status

async def execute_get_all_users(conn: asyncpg.Connection) -> List[Dict]:
    query = '''
    SELECT * FROM get_all_users();
    '''
    result = await conn.fetch(query)
    return [dict(record) for record in result]

async def execute_get_user_by_id(conn: asyncpg.Connection, user_id: UUID) -> Optional[Dict]:
    query = '''
    SELECT * FROM get_user_by_id($1);
    '''
    result = await conn.fetchrow(query, user_id)
    return dict(result) if result else None

async def execute_delete_user(conn: asyncpg.Connection, user_id: UUID) -> None:
    try:
        await conn.execute('SELECT delete_user_by_id($1)', user_id)
    except asyncpg.exceptions.RaiseException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

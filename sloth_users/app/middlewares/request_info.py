from fastapi.requests import Request
from pydantic.networks import IPvAnyAddress
from fastapi import Depends, Header

from app.db.procedures import log_request
from app.db import get_db

async def set_request_info(
        request: Request,
        conn = Depends(get_db),
        user_agent: str = Header(
            default=None,
            include_in_schema=False,
        ),
        cookie: str = Header(
            default=None,
            include_in_schema=False,
        ),
        real_ip: IPvAnyAddress | None = Header(
            default=None,
            alias='x-real-ip',
            include_in_schema=False,
        ),
        referer: str | None = Header(
            default=None,
            include_in_schema=False
        )
) -> None:
    await log_request(
        conn=conn,
        user_agent=user_agent,
        cookie=cookie,
        real_ip=str(real_ip) if real_ip else None,
        referer=referer
    )
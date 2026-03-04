from datetime import datetime

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_db_session
from app.models import AdminUser, Device
from app.utils.security import decode_token, verify_secret

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/auth/login")


async def get_db(session: AsyncSession = Depends(get_db_session)) -> AsyncSession:
    return session


async def get_current_admin(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> AdminUser:
    subject = decode_token(token)
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    admin = await session.get(AdminUser, subject)
    if admin is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return admin


async def get_current_device(
    api_key: str | None = Header(None, alias="X-API-Key"),
    session: AsyncSession = Depends(get_db_session),
) -> Device:
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")

    result = await session.execute(select(Device))
    devices = result.scalars().all()
    for device in devices:
        if verify_secret(api_key, device.api_key_hash):
            if device.status != "active":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Device disabled"
                )
            device.last_seen_at = datetime.utcnow()
            await session.commit()
            return device

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

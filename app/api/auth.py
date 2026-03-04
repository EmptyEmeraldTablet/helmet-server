from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session
from app.dependencies import get_current_admin
from app.models import AdminUser
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.common import ApiResponse
from app.utils.security import create_access_token, verify_secret

router = APIRouter()


@router.post("/auth/login", response_model=ApiResponse[TokenResponse])
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[TokenResponse]:
    result = await session.execute(
        select(AdminUser).where(AdminUser.username == payload.username)
    )
    admin = result.scalar_one_or_none()
    if admin is None or not verify_secret(payload.password, admin.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(admin.id)
    return ApiResponse(code=0, message="success", data=TokenResponse(access_token=token))


@router.post("/auth/refresh", response_model=ApiResponse[TokenResponse])
async def refresh_token(
    admin: AdminUser = Depends(get_current_admin),
) -> ApiResponse[TokenResponse]:
    token = create_access_token(admin.id)
    return ApiResponse(code=0, message="success", data=TokenResponse(access_token=token))

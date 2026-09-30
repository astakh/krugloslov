"""Authentication router."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user, get_refresh_token_from_cookie
from app.exceptions import AppException
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserInfo,
)
from app.security import auth_rate_limiter
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request."""
    # Check for X-Forwarded-For header (for proxied requests)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    # Fallback to direct client IP
    if request.client:
        return request.client.host
    return "unknown"


@router.post("/register", response_model=TokenResponse)
async def register(
    request: Request,
    body: RegisterRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    """Register a new user.

    Returns access token in response body and refresh token in httpOnly cookie.
    """
    # Rate limiting by IP
    client_ip = get_client_ip(request)
    allowed, retry_after = auth_rate_limiter.check_rate_limit(client_ip)
    if not allowed:
        raise AppException(
            code="rate_limit",
            message="Слишком много запросов. Попробуйте позже.",
            status_code=429,
            details={"retry_after": retry_after},
        )

    # Register user
    auth_service = AuthService(session)
    user, access_token, refresh_token = await auth_service.register(
        body.email, body.password
    )

    # Set refresh token cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,  # 30 days
        path="/auth",
    )

    return TokenResponse(access_token=access_token)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    """Authenticate user and issue tokens.

    Returns access token in response body and refresh token in httpOnly cookie.
    """
    # Rate limiting by IP
    client_ip = get_client_ip(request)
    allowed, retry_after = auth_rate_limiter.check_rate_limit(client_ip)
    if not allowed:
        raise AppException(
            code="rate_limit",
            message="Слишком много запросов. Попробуйте позже.",
            status_code=429,
            details={"retry_after": retry_after},
        )

    # Check if email is locked out due to failed attempts
    locked, lockout_retry_after = auth_rate_limiter.is_locked(body.email)
    if locked:
        raise AppException(
            code="account_locked",
            message="Слишком много неудачных попыток. Аккаунт временно заблокирован.",
            status_code=429,
            details={"retry_after": lockout_retry_after},
        )

    # Attempt login
    auth_service = AuthService(session)
    try:
        user, access_token, refresh_token = await auth_service.login(
            body.email, body.password
        )
        # Success — reset failure counter
        auth_rate_limiter.record_success(body.email)
    except Exception:
        # Failed — record failure
        auth_rate_limiter.record_failure(body.email)
        raise

    # Set refresh token cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,  # 30 days
        path="/auth",
    )

    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    refresh_token: str = Depends(get_refresh_token_from_cookie),
    session: AsyncSession = Depends(get_session),
):
    """Refresh access and refresh tokens.

    Implements token rotation with family tracking.
    Returns new access token in response body and new refresh token in cookie.
    """
    auth_service = AuthService(session)
    new_access_token, new_refresh_token = await auth_service.refresh(refresh_token)

    # Set new refresh token cookie
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,  # 30 days
        path="/auth",
    )

    return TokenResponse(access_token=new_access_token)


@router.post("/logout")
async def logout(
    response: Response,
    refresh_token: str = Depends(get_refresh_token_from_cookie),
    session: AsyncSession = Depends(get_session),
):
    """Logout user by revoking the refresh token.

    Clears the refresh token cookie.
    """
    auth_service = AuthService(session)
    await auth_service.logout(refresh_token)

    # Clear refresh token cookie
    response.delete_cookie(
        key="refresh_token",
        path="/auth",
    )

    return {"message": "Вы успешно вышли из системы"}


@router.get("/me", response_model=UserInfo)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """Get current authenticated user information.

    Returns only safe fields (no password hash).
    """
    return UserInfo(
        id=current_user.id,
        email=current_user.email,
        is_onboarded=current_user.is_onboarded,
        is_admin=current_user.is_admin,
    )

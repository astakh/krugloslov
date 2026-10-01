"""Dashboard router."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.dashboard import DashboardSummary
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def get_summary(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DashboardSummary:
    """
    Get dashboard summary.
    
    Returns profile info, lessons today, words summary, streak, and CTA.
    
    Raises:
        409: If user has not completed onboarding
    """
    from app.exceptions import AppException
    
    if not current_user.is_onboarded:
        raise AppException(
            status_code=409,
            code="onboarding_required",
            message="Please complete onboarding first"
        )
    
    service = DashboardService(session, current_user)
    return await service.get_summary()

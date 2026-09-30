"""Onboarding router."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.onboarding import OnboardingRequest, OnboardingResponse
from app.services.onboarding import OnboardingService

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.post("/complete", response_model=OnboardingResponse)
async def complete_onboarding(
    request: OnboardingRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> OnboardingResponse:
    """
    Complete user onboarding.
    
    Creates learning profile and marks user as onboarded.
    """
    service = OnboardingService(session)
    await service.complete_onboarding(
        user=current_user,
        timezone=request.timezone,
        level=request.level,
    )
    return OnboardingResponse()

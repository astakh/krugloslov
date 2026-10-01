"""Learning profile router."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.profile import (
    LearningProfileResponse,
    LearningProfileUpdateRequest,
    LearningProfileUpdateResponse,
)
from app.services.learning_profile_service import LearningProfileService

router = APIRouter(prefix="/learning-profile", tags=["learning-profile"])


@router.get("", response_model=LearningProfileResponse)
async def get_learning_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get learning profile settings.
    
    Returns:
    - Level
    - Active dictionary
    - Daily lesson limit
    - Learning statistics
    """
    service = LearningProfileService(session, current_user)
    return await service.get_profile()


@router.patch("", response_model=LearningProfileUpdateResponse)
async def update_learning_profile(
    request: LearningProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Update learning profile settings.
    
    Rules:
    - Level: A1-B2, affects only new word selection
    - Dictionary: existing words remain in review
    - Daily limit: 1 to DAILY_LESSON_LIMIT_MAX, applies immediately
    - In-progress lessons are not affected
    """
    service = LearningProfileService(session, current_user)
    return await service.update_profile(
        level=request.level,
        dictionary_id=request.dictionary_id,
        daily_lesson_limit=request.daily_lesson_limit,
        words_per_lesson=request.words_per_lesson,
    )

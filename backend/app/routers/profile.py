"""Profile router."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.profile import ProfileStatsResponse
from app.services.profile_stats_service import ProfileStatsService

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/stats", response_model=ProfileStatsResponse)
async def get_profile_stats(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get profile statistics.
    
    Returns:
    - Current and longest streak
    - Accuracy (30 days and all time)
    - Words count by status
    - Completed lessons count
    - Activity heatmap (last 12 months)
    """
    service = ProfileStatsService(session, current_user)
    return await service.get_stats()

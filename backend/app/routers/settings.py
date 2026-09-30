"""Settings router."""

from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user
from app.models.user import User
from app.services.timezone_service import TimezoneService

router = APIRouter(prefix="/settings", tags=["settings"])


class TimezoneUpdateRequest(BaseModel):
    """Request for timezone update."""
    timezone: str


class TimezoneUpdateResponse(BaseModel):
    """Response for timezone update."""
    today: str
    lessons_today: int
    resets_at: str
    current_streak: int
    longest_streak: int


@router.patch("/timezone", response_model=TimezoneUpdateResponse)
async def update_timezone(
    request: TimezoneUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Update user's timezone.
    
    Rules:
    - Must be valid IANA timezone
    - Can only be changed once per 7 days
    - Historical dates are not recalculated
    - Returns updated profile information
    """
    service = TimezoneService(session, current_user)
    return await service.change_timezone(request.timezone)

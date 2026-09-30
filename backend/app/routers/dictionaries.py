"""Dictionaries router."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.profile import DictionariesListResponse
from app.services.dictionaries_service import DictionariesService

router = APIRouter(prefix="/dictionaries", tags=["dictionaries"])


@router.get("", response_model=DictionariesListResponse)
async def get_dictionaries(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get list of all dictionaries.
    
    Returns:
    - id, code, name, description
    - is_general flag
    - words_total count
    """
    service = DictionariesService(session)
    return await service.get_dictionaries()

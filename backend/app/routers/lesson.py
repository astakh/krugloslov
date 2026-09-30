"""Lesson router."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user
from app.exceptions import AppException
from app.models.user import User
from app.schemas.lesson import DeclineWordRequest, DeclineWordResponse
from app.services.lesson_preview_service import LessonPreviewService

router = APIRouter(prefix="/lesson", tags=["lesson"])


@router.post("/preview")
async def preview_lesson(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Preview lesson word selection without creating anything.
    
    Returns state based on current conditions:
    - resume: if there's an in-progress lesson
    - limit_reached: if daily limit is reached
    - ready: if lesson can be started
    - no_words: if no words are available
    """
    # Check onboarding
    if not current_user.is_onboarded:
        raise AppException(
            status_code=409,
            code="onboarding_required",
            message="Требуется завершение онбординга"
        )

    service = LessonPreviewService(session, current_user)
    return await service.preview()


@router.post("/new-word/decline", response_model=DeclineWordResponse)
async def decline_new_word(
    request: DeclineWordRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Decline a new word and recalculate preview.
    
    The declined word will be marked as ignored and won't be offered again.
    Preview is recalculated with the next word by rank.
    """
    service = LessonPreviewService(session, current_user)
    preview = await service.decline_word(request.word_id)
    
    return DeclineWordResponse(
        message="Слово успешно отклонено",
        preview=preview,
    )

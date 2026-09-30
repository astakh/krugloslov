"""Vocabulary router for user's personal dictionary."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.vocabulary import (
    ChangeStatusRequest,
    ChangeStatusResponse,
    VocabularyListResponse,
    VocabularyWordDetail,
)
from app.services.vocabulary_service import VocabularyService

router = APIRouter(prefix="/vocabulary", tags=["vocabulary"])


@router.get("/list", response_model=VocabularyListResponse)
async def get_vocabulary_list(
    status: str | None = Query(None, description="Filter by status: active/mastered/ignored"),
    q: str | None = Query(None, description="Search by lemma or translations"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=50, description="Items per page"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get user's vocabulary list with filtering and search.

    - Filter by status (active/mastered/ignored)
    - Search by lemma or translations (case-insensitive)
    - Sorted alphabetically by lemma
    - Paginated (max 50 items per page)
    """
    service = VocabularyService(session, current_user)
    return await service.get_vocabulary_list(
        status=status, search=q, page=page, page_size=page_size
    )


@router.get("/word/{word_id}", response_model=VocabularyWordDetail)
async def get_word_detail(
    word_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get detailed information about a word including context history.

    Returns:
    - Word details (lemma, pos, translations, status, stage)
    - Due in lessons count
    - Last 20 context sentences from completed lessons
    """
    service = VocabularyService(session, current_user)
    return await service.get_word_detail(word_id)


@router.patch("/word/{word_id}/status", response_model=ChangeStatusResponse)
async def change_word_status(
    word_id: int,
    request: ChangeStatusRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Change word status.

    Allowed transitions:
    - active → ignored (removes from due list)
    - ignored → active (resets to stage 0, due next lesson)
    - mastered → active (resets to stage 0, due next lesson)

    Idempotent: setting same status returns success.
    """
    service = VocabularyService(session, current_user)
    message = await service.change_status(word_id, request.status)
    return ChangeStatusResponse(
        message=message, word_id=word_id, new_status=request.status
    )

"""Admin prompts router for LLM prompt management."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import require_admin
from app.models import User
from app.schemas.admin_prompts import (
    PromptDetail,
    PromptHistoryListResponse,
    PromptListItem,
    PromptUpdateRequest,
    RollbackRequest,
)
from app.services.admin_prompts_service import AdminPromptsService

router = APIRouter(prefix="/admin/prompts", tags=["admin"])


@router.get("", response_model=List[PromptListItem])
async def list_prompts(
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """List all prompts (metadata only)."""
    service = AdminPromptsService(session, admin)
    return await service.list_prompts()


@router.get("/{key}", response_model=PromptDetail)
async def get_prompt(
    key: str,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Get full prompt detail by key."""
    service = AdminPromptsService(session, admin)
    return await service.get_prompt(key)


@router.put("/{key}", response_model=PromptDetail)
async def update_prompt(
    key: str,
    request: PromptUpdateRequest,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Update prompt with validation and history."""
    service = AdminPromptsService(session, admin)
    return await service.update_prompt(key, request.system_template)


@router.get("/{key}/history", response_model=PromptHistoryListResponse)
async def get_prompt_history(
    key: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Get prompt history with pagination."""
    service = AdminPromptsService(session, admin)
    return await service.get_history(key, page, page_size)


@router.post("/{key}/rollback", response_model=PromptDetail)
async def rollback_prompt(
    key: str,
    request: RollbackRequest,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Rollback prompt to a specific history version."""
    service = AdminPromptsService(session, admin)
    return await service.rollback(key, request.history_id)

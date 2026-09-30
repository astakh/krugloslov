"""Schemas for admin prompts management."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class PromptListItem(BaseModel):
    """Prompt item for list view."""
    key: str
    updated_at: Optional[datetime]
    updated_by: Optional[int]


class PromptDetail(BaseModel):
    """Full prompt detail."""
    key: str
    system_template: str
    required_placeholders: List[str]
    updated_at: Optional[datetime]
    updated_by: Optional[int]


class PromptUpdateRequest(BaseModel):
    """Request to update prompt."""
    system_template: str = Field(..., min_length=1, max_length=8000)


class PromptHistoryItem(BaseModel):
    """History item."""
    id: int
    system_template: str
    created_at: datetime
    created_by: Optional[int]


class PromptHistoryListResponse(BaseModel):
    """Paginated history response."""
    items: List[PromptHistoryItem]
    total: int
    page: int
    page_size: int


class RollbackRequest(BaseModel):
    """Request to rollback to history version."""
    history_id: int

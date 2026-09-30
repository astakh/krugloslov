"""Schemas for admin reports and users endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


# === Reports ===

class TargetWordInfo(BaseModel):
    """Target word info for report."""
    word_id: int
    lemma: str
    pos: str
    surface_form: Optional[str] = None


class AdminReportItem(BaseModel):
    """Report item for admin list."""
    id: int
    user_id: int
    user_email: str
    exercise_id: int
    target_sentence: str
    reference_translation: str
    user_translation: Optional[str]
    target_words: List[TargetWordInfo]
    reason: str
    comment: str
    status: str
    admin_note: Optional[str]
    created_at: datetime
    llm_call_ids: List[int]


class AdminReportsListResponse(BaseModel):
    """Response for GET /admin/reports."""
    reports: List[AdminReportItem]
    total: int
    page: int
    page_size: int


class ProcessReportRequest(BaseModel):
    """Request for PATCH /admin/reports/{id}."""
    status: str = "processed"
    admin_note: Optional[str] = None


class ProcessReportResponse(BaseModel):
    """Response for PATCH /admin/reports/{id}."""
    message: str
    report_id: int


# === Users ===

class AdminUserItem(BaseModel):
    """User item for admin list."""
    id: int
    email: str
    is_onboarded: bool
    is_admin: bool
    created_at: datetime


class AdminUsersListResponse(BaseModel):
    """Response for GET /admin/users."""
    users: List[AdminUserItem]
    total: int
    page: int
    page_size: int


class ResetPasswordResponse(BaseModel):
    """Response for POST /admin/users/{id}/reset-password."""
    message: str
    user_id: int
    temporary_password: str

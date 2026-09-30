"""Admin router for dictionary and user management."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import require_admin
from app.models.dictionary import Dictionary
from app.schemas.admin import DryRunReport, ImportReport
from app.schemas.admin_management import (
    AdminReportsListResponse,
    AdminUsersListResponse,
    ProcessReportRequest,
    ProcessReportResponse,
    ResetPasswordResponse,
)
from app.services.admin_reports_service import AdminReportsService
from app.services.admin_users_service import AdminUsersService
from app.services.dictionary_import import DictionaryImportService

router = APIRouter(prefix="/admin/dictionaries", tags=["admin"])


@router.get("", response_model=List[dict])
async def list_dictionaries(
    admin=Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """List all dictionaries.

    Returns:
        List of dictionaries with id, code, name, description, is_general.
    """
    result = await session.execute(select(Dictionary))
    dictionaries = result.scalars().all()

    return [
        {
            "id": d.id,
            "code": d.code,
            "name": d.name,
            "description": d.description,
            "is_general": d.is_general,
        }
        for d in dictionaries
    ]


@router.post("/import", response_model=ImportReport)
async def import_dictionary(
    file: UploadFile = File(...),
    dry_run: bool = Query(False, description="If true, only validate without writing"),
    admin=Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Import dictionary from JSON file.

    Args:
        file: JSON file to import.
        dry_run: If True, only validate without writing.
        admin: Admin user (from dependency).
        session: Database session.

    Returns:
        Import report with statistics and errors.
    """
    # Read file content
    content = await file.read()

    # Check file size (10 MB limit)
    if len(content) > 10 * 1024 * 1024:
        from app.exceptions import ValidationException
        raise ValidationException(message="File too large (max 10 MB)")

    # Import dictionary
    service = DictionaryImportService(session)
    try:
        report, sha256 = await service.import_dictionary(
            admin_id=admin.id,
            file_name=file.filename or "unknown.json",
            file_content=content,
            dry_run=dry_run,
        )
    except ValueError as e:
        from app.exceptions import ValidationException
        raise ValidationException(message=str(e))

    await session.commit()

    return report


@router.post("/import/dry-run", response_model=DryRunReport)
async def import_dictionary_dry_run(
    file: UploadFile = File(...),
    admin=Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Dry-run import: validate only without writing.

    This is an alternative endpoint for explicit dry-run.

    Args:
        file: JSON file to validate.
        admin: Admin user (from dependency).
        session: Database session.

    Returns:
        Dry-run report with validation results.
    """
    # Read file content
    content = await file.read()

    # Check file size (10 MB limit)
    if len(content) > 10 * 1024 * 1024:
        from app.exceptions import ValidationException
        raise ValidationException(message="File too large (max 10 MB)")

    # Import dictionary in dry-run mode
    service = DictionaryImportService(session)
    try:
        report, sha256 = await service.import_dictionary(
            admin_id=admin.id,
            file_name=file.filename or "unknown.json",
            file_content=content,
            dry_run=True,
        )
    except ValueError as e:
        from app.exceptions import ValidationException
        raise ValidationException(message=str(e))

    return report


# === Reports Management ===

reports_router = APIRouter(prefix="/admin/reports", tags=["admin"])


@reports_router.get("", response_model=AdminReportsListResponse)
async def list_reports(
    status: Optional[str] = Query(None, description="Filter by status: new/processed"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    admin=Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    Get paginated list of user reports.
    
    Returns reports with exercise details, target words, and related LLM calls.
    """
    service = AdminReportsService(session, admin)
    return await service.get_reports(status=status, page=page, page_size=page_size)


@reports_router.patch("/{report_id}", response_model=ProcessReportResponse)
async def process_report(
    report_id: int,
    request: ProcessReportRequest,
    admin=Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    Process a report (mark as processed with admin note).
    
    Idempotent: processing same report with same note returns success.
    """
    service = AdminReportsService(session, admin)
    message = await service.process_report(
        report_id=report_id,
        status=request.status,
        admin_note=request.admin_note,
    )
    return ProcessReportResponse(message=message, report_id=report_id)


# === Users Management ===

users_router = APIRouter(prefix="/admin/users", tags=["admin"])


@users_router.get("", response_model=AdminUsersListResponse)
async def list_users(
    search: Optional[str] = Query(None, description="Search by email"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    admin=Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    Get paginated list of users.
    
    Does not return password_hash or token information.
    """
    service = AdminUsersService(session, admin)
    return await service.get_users(search=search, page=page, page_size=page_size)


@users_router.post("/{user_id}/reset-password", response_model=ResetPasswordResponse)
async def reset_user_password(
    user_id: int,
    admin=Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    Reset user's password and revoke all sessions.
    
    Generates a temporary password and returns it once.
    All refresh tokens are revoked.
    """
    service = AdminUsersService(session, admin)
    temporary_password, message = await service.reset_password(user_id)
    
    return ResetPasswordResponse(
        message=message,
        user_id=user_id,
        temporary_password=temporary_password,
    )

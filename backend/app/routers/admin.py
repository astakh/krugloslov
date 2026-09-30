"""Admin router for dictionary management."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import require_admin
from app.models.dictionary import Dictionary
from app.schemas.admin import DryRunReport, ImportReport
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

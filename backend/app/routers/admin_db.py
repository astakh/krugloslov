"""Admin database browser router (read-only)."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import require_admin
from app.schemas.admin_db import TableDataResponse, TableInfo
from app.services.admin_db_service import AdminDbService

router = APIRouter(prefix="/admin/db", tags=["admin"])


@router.get("/tables", response_model=List[TableInfo])
async def list_tables(
    admin=Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    Get list of all user tables with approximate row counts.
    
    Read-only access. Uses pg_class.reltuples for fast estimates.
    Excludes technical tables like alembic_version.
    """
    service = AdminDbService(session)
    return await service.get_tables()


@router.get("/tables/{table_name}", response_model=TableDataResponse)
async def get_table_data(
    table_name: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=1, le=100, description="Items per page"),
    order_by: Optional[str] = Query(None, description="Column to sort by"),
    order_dir: str = Query("asc", description="Sort direction: asc or desc"),
    search: Optional[str] = Query(None, description="Search in text columns"),
    admin=Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    Get paginated table data with sorting and search.
    
    Read-only access. Sensitive columns are masked.
    All identifiers are safely escaped.
    """
    service = AdminDbService(session)
    return await service.get_table_data(
        table_name=table_name,
        page=page,
        page_size=page_size,
        order_by=order_by,
        order_dir=order_dir,
        search=search,
    )

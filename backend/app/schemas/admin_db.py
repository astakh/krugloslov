"""Schemas for admin database browser."""

from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel


class TableInfo(BaseModel):
    """Basic table information."""
    table_name: str
    row_count_estimate: int
    columns_count: int


class ColumnInfo(BaseModel):
    """Column information with masking flag."""
    name: str
    type: str
    is_primary_key: bool
    masked: bool


class TableDataResponse(BaseModel):
    """Response for table data browsing."""
    table_name: str
    columns: List[ColumnInfo]
    rows: List[dict[str, Any]]
    page: int
    page_size: int
    total: Optional[int]

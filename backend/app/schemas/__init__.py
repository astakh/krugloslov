"""Pydantic schemas for error responses."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Single error object in the unified error format."""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Unified error response envelope."""
    error: ErrorDetail

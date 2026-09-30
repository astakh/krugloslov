"""Custom application exceptions."""

from __future__ import annotations

from typing import Any, Dict, Optional


class AppException(Exception):
    """Base application exception with structured error info."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class NotFoundException(AppException):
    """Resource not found."""

    def __init__(self, message: str = "Ресурс не найден", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="not_found",
            message=message,
            status_code=404,
            details=details,
        )


class ValidationException(AppException):
    """Validation error."""

    def __init__(self, message: str = "Ошибка валидации", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="validation_error",
            message=message,
            status_code=422,
            details=details,
        )


class UnauthorizedException(AppException):
    """Authentication required."""

    def __init__(self, message: str = "Требуется авторизация", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="unauthorized",
            message=message,
            status_code=401,
            details=details,
        )


class ForbiddenException(AppException):
    """Access denied."""

    def __init__(self, message: str = "Доступ запрещён", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="forbidden",
            message=message,
            status_code=403,
            details=details,
        )


class RateLimitException(AppException):
    """Rate limit exceeded."""

    def __init__(self, message: str = "Превышен лимит запросов", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="rate_limit",
            message=message,
            status_code=429,
            details=details,
        )

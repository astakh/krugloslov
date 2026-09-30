"""FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.exceptions import AppException
from app.middleware import RequestLoggingMiddleware
from app.routers.admin import reports_router, router as admin_router, users_router
from app.routers.admin_db import router as admin_db_router
from app.routers.admin_prompts import router as admin_prompts_router
from app.routers.auth import router as auth_router
from app.routers.dashboard import router as dashboard_router
from app.routers.dictionaries import router as dictionaries_router
from app.routers.health import router as health_router
from app.routers.learning_profile import router as learning_profile_router
from app.routers.lesson import router as lesson_router
from app.routers.onboarding import router as onboarding_router
from app.routers.profile import router as profile_router
from app.routers.settings import router as settings_router
from app.routers.vocabulary import router as vocabulary_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("krugloslov")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    logger.info("Starting Круглослов API")
    logger.info("WORDS_PER_LESSON=%d", settings.WORDS_PER_LESSON)
    logger.info("DAILY_LESSON_LIMIT_DEFAULT=%d", settings.DAILY_LESSON_LIMIT_DEFAULT)
    logger.info("DAILY_LESSON_LIMIT_MAX=%d", settings.DAILY_LESSON_LIMIT_MAX)
    yield
    logger.info("Shutting down Круглослов API")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Круглослов API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request logging
    app.add_middleware(RequestLoggingMiddleware)

    # --- Exception handlers ---

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        """Handle custom application exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle Pydantic validation errors in request bodies."""
        details = []
        for error in exc.errors():
            details.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
            })
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Ошибка валидации запроса",
                    "details": {"fields": details},
                }
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Catch-all handler for unhandled exceptions."""
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "Внутренняя ошибка сервера",
                    "details": {},
                }
            },
        )

    # --- Routers ---
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(onboarding_router)
    app.include_router(dashboard_router)
    app.include_router(admin_router)
    app.include_router(reports_router)
    app.include_router(users_router)
    app.include_router(admin_db_router)
    app.include_router(admin_prompts_router)
    app.include_router(lesson_router)
    app.include_router(vocabulary_router)
    app.include_router(profile_router)
    app.include_router(settings_router)
    app.include_router(learning_profile_router)
    app.include_router(dictionaries_router)

    return app


app = create_app()

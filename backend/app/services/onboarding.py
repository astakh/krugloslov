"""Onboarding service."""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import AppException
from app.models.dictionary import Dictionary
from app.models.learning_profile import LearningProfile
from app.models.user import User
from app.services.events import record_event

logger = logging.getLogger(__name__)


class OnboardingService:
    """Service for handling user onboarding."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def complete_onboarding(
        self,
        user: User,
        timezone: str,
        level: str,
    ) -> None:
        """
        Complete user onboarding.
        
        Args:
            user: User to onboard
            timezone: IANA timezone string
            level: CEFR level (A1-B2)
            
        Raises:
            AppException: If user already onboarded or general dictionary missing
        """
        # Check if already onboarded
        if user.is_onboarded:
            raise AppException(
                status_code=409,
                code="already_onboarded",
                message="Пользователь уже завершил онбординг"
            )

        # Find general dictionary
        general_dict = await self._get_general_dictionary()
        if not general_dict:
            logger.error("General dictionary not found during onboarding")
            raise AppException(
                status_code=503,
                code="general_dictionary_missing",
                message="Общий словарь не найден. Обратитесь к администратору."
            )

        # Update user
        user.timezone = timezone
        user.is_onboarded = True
        # Note: timezone_changed_at is NOT updated during onboarding per requirements

        # Create learning profile
        profile = LearningProfile(
            user_id=user.id,
            level=level,
            dictionary_id=general_dict.id,
            daily_lesson_limit=settings.DAILY_LESSON_LIMIT_DEFAULT,
            last_lesson_number=0,
        )
        self.session.add(profile)

        # Record event
        await record_event(
            self.session,
            user.id,
            "onboarding_completed",
            {"timezone": timezone, "level": level}
        )

        await self.session.commit()

    async def _get_general_dictionary(self) -> Optional[Dictionary]:
        """Get the general dictionary."""
        result = await self.session.execute(
            select(Dictionary).where(Dictionary.is_general == True)
        )
        return result.scalar_one_or_none()

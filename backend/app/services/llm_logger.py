"""LLM call logging service."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm_call import LLMCall

logger = logging.getLogger(__name__)


class LlmLogger:
    """Service for logging LLM API calls to database."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def log_call(
        self,
        purpose: str,
        user_id: int,
        request_data: dict[str, Any],
        response_data: Optional[dict[str, Any]],
        status: str,
        http_status: Optional[int] = None,
        latency_ms: Optional[int] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        lesson_id: Optional[int] = None,
        exercise_id: Optional[int] = None,
        attempt: int = 1,
    ) -> None:
        """
        Log an LLM API call.
        
        Args:
            purpose: 'generate' or 'evaluate'
            user_id: User ID
            request_data: Request payload
            response_data: Response payload (None on error)
            status: Call status (ok, http_error, timeout, etc.)
            http_status: HTTP status code
            latency_ms: Request latency in milliseconds
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            lesson_id: Optional lesson ID
            exercise_id: Optional exercise ID
            attempt: Attempt number (for retries)
        """
        try:
            call = LLMCall(
                purpose=purpose,
                user_id=user_id,
                lesson_id=lesson_id,
                exercise_id=exercise_id,
                attempt=attempt,
                request=request_data,
                response=response_data,
                status=status,
                http_status=http_status,
                latency_ms=latency_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                created_at=datetime.now(timezone.utc),
            )
            
            self.session.add(call)
            await self.session.commit()
            
            logger.debug(
                f"Logged LLM call: purpose={purpose}, status={status}, "
                f"latency={latency_ms}ms, tokens={prompt_tokens}+{completion_tokens}"
            )
            
        except Exception as e:
            # Don't fail the main operation if logging fails
            logger.error(f"Failed to log LLM call: {e}", exc_info=True)
            # Rollback to clean state
            await self.session.rollback()

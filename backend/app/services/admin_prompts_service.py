"""Service for admin prompts management with validation and history."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import AppException
from app.models import Prompt, PromptHistory, User
from app.schemas.admin_prompts import (
    PromptDetail,
    PromptHistoryItem,
    PromptHistoryListResponse,
    PromptListItem,
)

logger = logging.getLogger(__name__)

# Fixed prompt keys - cannot create new ones through admin
ALLOWED_PROMPT_KEYS = {"generate_sentences", "evaluate_translation"}

# Required and allowed placeholders per prompt
PROMPT_PLACEHOLDERS: Dict[str, Dict[str, Any]] = {
    "generate_sentences": {
        "required": {"level"},
        "allowed": {"level"},
    },
    "evaluate_translation": {
        "required": set(),
        "allowed": set(),
    },
}

# Test values for template validation
TEST_VALUES: Dict[str, Dict[str, str]] = {
    "generate_sentences": {"level": "B1"},
    "evaluate_translation": {},
}


class AdminPromptsService:
    """Service for managing LLM prompts with validation and history."""

    def __init__(self, session: AsyncSession, admin: User):
        self.session = session
        self.admin = admin

    async def list_prompts(self) -> List[PromptListItem]:
        """List all prompts (metadata only, no template text)."""
        result = await self.session.execute(
            select(Prompt).order_by(Prompt.key)
        )
        prompts = result.scalars().all()
        
        return [
            PromptListItem(
                key=p.key,
                updated_at=p.updated_at,
                updated_by=p.updated_by,
            )
            for p in prompts
        ]

    async def get_prompt(self, key: str) -> PromptDetail:
        """Get full prompt detail by key."""
        if key not in ALLOWED_PROMPT_KEYS:
            raise AppException(
                status_code=404,
                code="prompt_not_found",
                message=f"Prompt '{key}' not found",
            )

        result = await self.session.execute(
            select(Prompt).where(Prompt.key == key)
        )
        prompt = result.scalar_one_or_none()

        if not prompt:
            raise AppException(
                status_code=404,
                code="prompt_not_found",
                message=f"Prompt '{key}' not found",
            )

        # Extract placeholders from template
        placeholders = self._extract_placeholders(prompt.system_template)

        return PromptDetail(
            key=prompt.key,
            system_template=prompt.system_template,
            required_placeholders=sorted(list(PROMPT_PLACEHOLDERS[key]["required"])),
            updated_at=prompt.updated_at,
            updated_by=prompt.updated_by,
        )

    async def update_prompt(self, key: str, system_template: str) -> PromptDetail:
        """Update prompt with validation and history."""
        # Validate key
        if key not in ALLOWED_PROMPT_KEYS:
            raise AppException(
                status_code=404,
                code="prompt_not_found",
                message=f"Prompt '{key}' not found",
            )

        # Validate template
        self._validate_template(key, system_template)

        # Start transaction
        async with self.session.begin():
            # Insert into history first
            history_entry = PromptHistory(
                key=key,
                system_template=system_template,
                created_at=datetime.now(timezone.utc),
                created_by=self.admin.id,
            )
            self.session.add(history_entry)

            # Update or create prompt
            result = await self.session.execute(
                select(Prompt).where(Prompt.key == key)
            )
            prompt = result.scalar_one_or_none()

            if prompt:
                prompt.system_template = system_template
                prompt.updated_at = datetime.now(timezone.utc)
                prompt.updated_by = self.admin.id
            else:
                # Create new prompt (should not happen for fixed keys, but handle it)
                prompt = Prompt(
                    key=key,
                    system_template=system_template,
                    updated_at=datetime.now(timezone.utc),
                    updated_by=self.admin.id,
                )
                self.session.add(prompt)

        # Return updated prompt
        return await self.get_prompt(key)

    async def get_history(
        self, key: str, page: int = 1, page_size: int = 20
    ) -> PromptHistoryListResponse:
        """Get prompt history with pagination."""
        if key not in ALLOWED_PROMPT_KEYS:
            raise AppException(
                status_code=404,
                code="prompt_not_found",
                message=f"Prompt '{key}' not found",
            )

        # Get total count
        count_result = await self.session.execute(
            select(func.count(PromptHistory.id)).where(PromptHistory.key == key)
        )
        total = count_result.scalar() or 0

        # Get paginated results
        offset = (page - 1) * page_size
        result = await self.session.execute(
            select(PromptHistory)
            .where(PromptHistory.key == key)
            .order_by(PromptHistory.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        items = result.scalars().all()

        return PromptHistoryListResponse(
            items=[
                PromptHistoryItem(
                    id=h.id,
                    system_template=h.system_template,
                    created_at=h.created_at,
                    created_by=h.created_by,
                )
                for h in items
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def rollback(self, key: str, history_id: int) -> PromptDetail:
        """Rollback prompt to a specific history version."""
        if key not in ALLOWED_PROMPT_KEYS:
            raise AppException(
                status_code=404,
                code="prompt_not_found",
                message=f"Prompt '{key}' not found",
            )

        # Get history entry
        result = await self.session.execute(
            select(PromptHistory).where(
                PromptHistory.id == history_id,
                PromptHistory.key == key,
            )
        )
        history_entry = result.scalar_one_or_none()

        if not history_entry:
            raise AppException(
                status_code=404,
                code="history_not_found",
                message=f"History entry {history_id} not found for prompt '{key}'",
            )

        # Validate the historical template
        self._validate_template(key, history_entry.system_template)

        # Update prompt with historical template
        return await self.update_prompt(key, history_entry.system_template)

    def _validate_template(self, key: str, template: str) -> None:
        """Validate prompt template for placeholders and syntax."""
        # Extract placeholders
        placeholders = self._extract_placeholders(template)
        
        # Check for unknown placeholders
        allowed = PROMPT_PLACEHOLDERS[key]["allowed"]
        unknown = placeholders - allowed
        if unknown:
            raise AppException(
                status_code=422,
                code="unknown_placeholder",
                message=f"Unknown placeholder(s): {', '.join(sorted(unknown))}",
                details={"unknown_placeholders": sorted(list(unknown))},
            )

        # Check for missing required placeholders
        required = PROMPT_PLACEHOLDERS[key]["required"]
        missing = required - placeholders
        if missing:
            raise AppException(
                status_code=422,
                code="missing_placeholder",
                message=f"Missing required placeholder(s): {', '.join(sorted(missing))}",
                details={"missing_placeholders": sorted(list(missing))},
            )

        # Test template rendering
        try:
            test_values = TEST_VALUES[key]
            template.format_map(test_values)
        except KeyError as e:
            raise AppException(
                status_code=422,
                code="invalid_template",
                message=f"Template has unresolved placeholder: {e}",
                details={"placeholder": str(e)},
            )
        except (ValueError, IndexError) as e:
            raise AppException(
                status_code=422,
                code="invalid_template",
                message=f"Template syntax error: {e}",
                details={"error": str(e)},
            )

    def _extract_placeholders(self, template: str) -> Set[str]:
        """Extract placeholder names from template, ignoring escaped braces."""
        # First, replace escaped braces {{ and }} with placeholders
        temp = template.replace("{{", "\x00").replace("}}", "\x01")
        
        # Find all {name} patterns
        pattern = r"\{([^{}]+)\}"
        matches = re.findall(pattern, temp)
        
        return set(matches)

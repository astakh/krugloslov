"""Tests for admin prompts service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.exceptions import AppException
from app.models import Prompt, PromptHistory, User
from app.services.admin_prompts_service import AdminPromptsService


class TestAdminPromptsService:
    """Tests for AdminPromptsService."""

    @pytest.fixture
    def mock_session(self):
        """Create mock session."""
        return AsyncMock()

    @pytest.fixture
    def mock_admin(self):
        """Create mock admin user."""
        admin = MagicMock(spec=User)
        admin.id = 1
        admin.email = "admin@example.com"
        admin.is_admin = True
        return admin

    @pytest.fixture
    def service(self, mock_session, mock_admin):
        """Create service instance."""
        return AdminPromptsService(mock_session, mock_admin)

    def test_extract_placeholders_simple(self, service):
        """Test extracting simple placeholders."""
        template = "Hello {name}, your level is {level}"
        placeholders = service._extract_placeholders(template)
        assert placeholders == {"name", "level"}

    def test_extract_placeholders_escaped(self, service):
        """Test extracting placeholders with escaped braces."""
        template = "Use {{curly braces}} and {actual_placeholder}"
        placeholders = service._extract_placeholders(template)
        assert placeholders == {"actual_placeholder"}

    def test_extract_placeholders_no_placeholders(self, service):
        """Test template without placeholders."""
        template = "This is a plain text template"
        placeholders = service._extract_placeholders(template)
        assert placeholders == set()

    def test_extract_placeholders_complex(self, service):
        """Test complex template with mixed braces."""
        template = "JSON: {{\"key\": \"{value}\"}} and {other}"
        placeholders = service._extract_placeholders(template)
        assert placeholders == {"value", "other"}

    def test_validate_template_valid_generate_sentences(self, service):
        """Test valid template for generate_sentences."""
        template = "Generate sentences for level {level}"
        # Should not raise
        service._validate_template("generate_sentences", template)

    def test_validate_template_missing_placeholder(self, service):
        """Test template with missing required placeholder."""
        template = "Generate sentences without level"
        with pytest.raises(AppException) as exc_info:
            service._validate_template("generate_sentences", template)
        assert exc_info.value.code == "missing_placeholder"
        assert "level" in exc_info.value.message

    def test_validate_template_unknown_placeholder(self, service):
        """Test template with unknown placeholder."""
        template = "Generate for level {level} and {unknown}"
        with pytest.raises(AppException) as exc_info:
            service._validate_template("generate_sentences", template)
        assert exc_info.value.code == "unknown_placeholder"
        assert "unknown" in exc_info.value.message

    def test_validate_template_invalid_syntax(self, service):
        """Test template with invalid syntax."""
        template = "Invalid {unclosed brace"
        with pytest.raises(AppException) as exc_info:
            service._validate_template("generate_sentences", template)
        assert exc_info.value.code == "invalid_template"

    def test_validate_template_evaluate_translation(self, service):
        """Test valid template for evaluate_translation (no placeholders)."""
        template = "Evaluate this translation"
        # Should not raise
        service._validate_template("evaluate_translation", template)

    def test_validate_template_evaluate_with_placeholder(self, service):
        """Test evaluate_translation template with placeholder (should fail)."""
        template = "Evaluate {something}"
        with pytest.raises(AppException) as exc_info:
            service._validate_template("evaluate_translation", template)
        assert exc_info.value.code == "unknown_placeholder"

    @pytest.mark.asyncio
    async def test_list_prompts(self, service, mock_session):
        """Test listing prompts."""
        # Mock query result
        mock_prompt = MagicMock(spec=Prompt)
        mock_prompt.key = "generate_sentences"
        mock_prompt.updated_at = None
        mock_prompt.updated_by = None
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_prompt]
        mock_session.execute.return_value = mock_result

        result = await service.list_prompts()
        
        assert len(result) == 1
        assert result[0].key == "generate_sentences"

    @pytest.mark.asyncio
    async def test_get_prompt_not_found(self, service):
        """Test getting non-existent prompt."""
        with pytest.raises(AppException) as exc_info:
            await service.get_prompt("nonexistent")
        assert exc_info.value.code == "prompt_not_found"

    @pytest.mark.asyncio
    async def test_update_prompt_invalid_key(self, service):
        """Test updating prompt with invalid key."""
        with pytest.raises(AppException) as exc_info:
            await service.update_prompt("invalid_key", "template")
        assert exc_info.value.code == "prompt_not_found"

    @pytest.mark.asyncio
    async def test_get_history_invalid_key(self, service):
        """Test getting history for invalid key."""
        with pytest.raises(AppException) as exc_info:
            await service.get_history("invalid_key")
        assert exc_info.value.code == "prompt_not_found"

    @pytest.mark.asyncio
    async def test_rollback_invalid_key(self, service):
        """Test rollback for invalid key."""
        with pytest.raises(AppException) as exc_info:
            await service.rollback("invalid_key", 1)
        assert exc_info.value.code == "prompt_not_found"


class TestPromptValidation:
    """Test prompt validation edge cases."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        mock_session = AsyncMock()
        mock_admin = MagicMock(spec=User)
        mock_admin.id = 1
        return AdminPromptsService(mock_session, mock_admin)

    def test_empty_template(self, service):
        """Test empty template."""
        with pytest.raises(AppException) as exc_info:
            service._validate_template("generate_sentences", "")
        assert exc_info.value.code == "missing_placeholder"

    def test_only_escaped_braces(self, service):
        """Test template with only escaped braces."""
        template = "{{escaped}} and {{more}}"
        with pytest.raises(AppException) as exc_info:
            service._validate_template("generate_sentences", template)
        assert exc_info.value.code == "missing_placeholder"

    def test_multiple_same_placeholder(self, service):
        """Test template with same placeholder multiple times."""
        template = "Level {level} is {level}"
        # Should not raise - same placeholder used multiple times is OK
        service._validate_template("generate_sentences", template)

    def test_nested_braces(self, service):
        """Test template with nested braces."""
        template = "{{outer {level} inner}}"
        # Should extract 'level' as placeholder
        placeholders = service._extract_placeholders(template)
        assert "level" in placeholders

"""Tests for prompt service."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.prompt_service import PromptService, FALLBACK_PROMPTS


class TestPromptService:
    """Tests for PromptService."""
    
    @pytest.mark.asyncio
    async def test_get_prompt_from_database(self):
        """Should return prompt from database if exists."""
        session = AsyncMock()
        
        # Mock database result
        mock_prompt = MagicMock()
        mock_prompt.system_template = "Custom prompt from DB"
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_prompt
        session.execute.return_value = mock_result
        
        service = PromptService(session)
        prompt = await service.get_prompt("generate_sentences")
        
        assert prompt == "Custom prompt from DB"
    
    @pytest.mark.asyncio
    async def test_get_prompt_fallback_when_missing(self):
        """Should return fallback prompt when not in database."""
        session = AsyncMock()
        
        # Mock empty database result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result
        
        service = PromptService(session)
        prompt = await service.get_prompt("generate_sentences")
        
        assert prompt == FALLBACK_PROMPTS["generate_sentences"]
    
    @pytest.mark.asyncio
    async def test_get_prompt_raises_on_unknown_key(self):
        """Should raise ValueError for unknown prompt key."""
        session = AsyncMock()
        
        # Mock empty database result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result
        
        service = PromptService(session)
        
        with pytest.raises(ValueError, match="No fallback prompt available"):
            await service.get_prompt("unknown_prompt_key")
    
    def test_format_prompt_with_placeholders(self):
        """Should format prompt with placeholders."""
        session = AsyncMock()
        service = PromptService(session)
        
        template = "Generate {count} sentences for {level} level with word: {word}"
        result = service.format_prompt(
            template,
            count=5,
            level="A2",
            word="run"
        )
        
        assert result == "Generate 5 sentences for A2 level with word: run"
    
    def test_format_prompt_raises_on_missing_placeholder(self):
        """Should raise ValueError on missing placeholder."""
        session = AsyncMock()
        service = PromptService(session)
        
        template = "Generate {count} sentences for {level} level"
        
        with pytest.raises(ValueError, match="Missing required placeholder"):
            service.format_prompt(template, count=5)  # Missing 'level'
    
    def test_fallback_prompts_have_required_placeholders(self):
        """Should verify fallback prompts have correct placeholders."""
        # generate_sentences should have {level}, {count}, {word}
        generate_prompt = FALLBACK_PROMPTS["generate_sentences"]
        assert "{level}" in generate_prompt
        assert "{count}" in generate_prompt
        assert "{word}" in generate_prompt
        
        # evaluate_translation should have no placeholders in system template
        evaluate_prompt = FALLBACK_PROMPTS["evaluate_translation"]
        # This prompt doesn't require placeholders in system template
        assert "JSON" in evaluate_prompt

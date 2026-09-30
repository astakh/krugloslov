"""Tests for GigaChat client with mocked HTTP responses."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm.client import GigaChatClient, TokenInfo
from app.llm.exceptions import (
    LlmInvalidResponse,
    LlmQuotaExceeded,
    LlmRefused,
    LlmUnavailable,
)
from app.llm.schemas import GenerateSentencesResponse


class TestTokenManagement:
    """Tests for OAuth token management."""
    
    @pytest.mark.asyncio
    async def test_token_refresh_on_expired(self):
        """Should refresh token when expired."""
        client = GigaChatClient()
        
        # Set expired token
        client._token = TokenInfo(
            access_token="old_token",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        
        # Mock HTTP response for token refresh
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_token",
            "expires_at": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp() * 1000)
        }
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            token = await client._get_token()
            
            assert token == "new_token"
            assert client._token.access_token == "new_token"
    
    @pytest.mark.asyncio
    async def test_token_refresh_within_120_seconds(self):
        """Should refresh token if expires within 120 seconds."""
        client = GigaChatClient()
        
        # Set token expiring in 60 seconds
        client._token = TokenInfo(
            access_token="old_token",
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=60)
        )
        
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_token",
            "expires_at": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp() * 1000)
        }
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            token = await client._get_token()
            
            assert token == "new_token"
    
    @pytest.mark.asyncio
    async def test_token_not_refreshed_if_valid(self):
        """Should not refresh token if valid for more than 120 seconds."""
        client = GigaChatClient()
        
        # Set valid token
        client._token = TokenInfo(
            access_token="valid_token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        token = await client._get_token()
        
        assert token == "valid_token"
    
    @pytest.mark.asyncio
    async def test_concurrent_token_refresh(self):
        """Should handle concurrent token refresh requests."""
        client = GigaChatClient()
        
        # Set expired token
        client._token = TokenInfo(
            access_token="old_token",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_token",
            "expires_at": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp() * 1000)
        }
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            # Make concurrent requests
            tasks = [client._get_token() for _ in range(5)]
            tokens = await asyncio.gather(*tasks)
            
            # All should get the same token
            assert all(t == "new_token" for t in tokens)
            
            # Should only refresh once (lock prevents multiple refreshes)
            assert mock_post.call_count == 1


class TestChatLayer:
    """Tests for Layer A (chat) method."""
    
    @pytest.mark.asyncio
    async def test_successful_chat(self):
        """Should return parsed response on success."""
        client = GigaChatClient()
        client._token = TokenInfo(
            access_token="test_token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {"content": "Test response"},
                "finish_reason": "stop"
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5}
        }
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            result = await client.chat(
                messages=[{"role": "user", "content": "Hello"}],
                temperature=0.7,
                max_tokens=100,
                timeout=10.0
            )
            
            assert result["content"] == "Test response"
            assert result["finish_reason"] == "stop"
            assert result["usage"]["prompt_tokens"] == 10
    
    @pytest.mark.asyncio
    async def test_401_retry_with_refresh(self):
        """Should retry with token refresh on 401."""
        client = GigaChatClient()
        client._token = TokenInfo(
            access_token="old_token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        # Mock 401 then 200
        mock_401 = MagicMock()
        mock_401.status_code = 401
        
        mock_200 = MagicMock()
        mock_200.status_code = 200
        mock_200.json.return_value = {
            "choices": [{
                "message": {"content": "Success after refresh"},
                "finish_reason": "stop"
            }],
            "usage": {}
        }
        
        # Mock token refresh
        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "access_token": "new_token",
            "expires_at": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp() * 1000)
        }
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = [mock_401, mock_200]
            
            result = await client.chat(
                messages=[{"role": "user", "content": "Hello"}],
                temperature=0.7,
                max_tokens=100,
                timeout=10.0
            )
            
            assert result["content"] == "Success after refresh"
    
    @pytest.mark.asyncio
    async def test_401_twice_raises_unavailable(self):
        """Should raise LlmUnavailable on second 401."""
        client = GigaChatClient()
        client._token = TokenInfo(
            access_token="old_token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        # Mock 401 twice
        mock_401 = MagicMock()
        mock_401.status_code = 401
        
        # Mock token refresh
        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "access_token": "new_token",
            "expires_at": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp() * 1000)
        }
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = [mock_401, mock_401]
            
            with pytest.raises(LlmUnavailable):
                await client.chat(
                    messages=[{"role": "user", "content": "Hello"}],
                    temperature=0.7,
                    max_tokens=100,
                    timeout=10.0
                )
    
    @pytest.mark.asyncio
    async def test_402_raises_quota_exceeded(self):
        """Should raise LlmQuotaExceeded on 402."""
        client = GigaChatClient()
        client._token = TokenInfo(
            access_token="test_token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        mock_response = MagicMock()
        mock_response.status_code = 402
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            with pytest.raises(LlmQuotaExceeded):
                await client.chat(
                    messages=[{"role": "user", "content": "Hello"}],
                    temperature=0.7,
                    max_tokens=100,
                    timeout=10.0
                )
    
    @pytest.mark.asyncio
    async def test_timeout_raises_unavailable(self):
        """Should raise LlmUnavailable on timeout."""
        client = GigaChatClient()
        client._token = TokenInfo(
            access_token="test_token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        import httpx
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Timeout")
            
            with pytest.raises(LlmUnavailable):
                await client.chat(
                    messages=[{"role": "user", "content": "Hello"}],
                    temperature=0.7,
                    max_tokens=100,
                    timeout=10.0
                )


class TestChatJsonLayer:
    """Tests for Layer B (chat_json) method."""
    
    @pytest.mark.asyncio
    async def test_successful_json_parsing(self):
        """Should parse valid JSON response."""
        client = GigaChatClient()
        client._token = TokenInfo(
            access_token="test_token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        # Mock response with JSON
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "sentences": [
                            {"english": "The cat runs fast", "russian": "Кот бегает быстро"}
                        ]
                    })
                },
                "finish_reason": "stop"
            }],
            "usage": {}
        }
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            result = await client.chat_json(
                messages=[{"role": "user", "content": "Generate sentences"}],
                validator=GenerateSentencesResponse,
                temperature=0.7,
                max_tokens=100,
                timeout=10.0,
                max_retries=0
            )
            
            assert isinstance(result, GenerateSentencesResponse)
            assert len(result.sentences) == 1
            assert result.sentences[0].english == "The cat runs fast"
    
    @pytest.mark.asyncio
    async def test_json_with_markdown_code_block(self):
        """Should extract JSON from markdown code block."""
        client = GigaChatClient()
        client._token = TokenInfo(
            access_token="test_token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        # Mock response with JSON in code block
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "```json\n" + json.dumps({
                        "sentences": [
                            {"english": "Test sentence", "russian": "Тестовое предложение"}
                        ]
                    }) + "\n```"
                },
                "finish_reason": "stop"
            }],
            "usage": {}
        }
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            result = await client.chat_json(
                messages=[{"role": "user", "content": "Generate"}],
                validator=GenerateSentencesResponse,
                temperature=0.7,
                max_tokens=100,
                timeout=10.0,
                max_retries=0
            )
            
            assert isinstance(result, GenerateSentencesResponse)
    
    @pytest.mark.asyncio
    async def test_invalid_json_retries(self):
        """Should retry on invalid JSON."""
        client = GigaChatClient()
        client._token = TokenInfo(
            access_token="test_token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        # Mock invalid then valid response
        mock_invalid = MagicMock()
        mock_invalid.status_code = 200
        mock_invalid.json.return_value = {
            "choices": [{
                "message": {"content": "Not valid JSON"},
                "finish_reason": "stop"
            }],
            "usage": {}
        }
        
        mock_valid = MagicMock()
        mock_valid.status_code = 200
        mock_valid.json.return_value = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "sentences": [{"english": "Test", "russian": "Тест"}]
                    })
                },
                "finish_reason": "stop"
            }],
            "usage": {}
        }
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = [mock_invalid, mock_valid]
            
            result = await client.chat_json(
                messages=[{"role": "user", "content": "Generate"}],
                validator=GenerateSentencesResponse,
                temperature=0.7,
                max_tokens=100,
                timeout=10.0,
                max_retries=1
            )
            
            assert isinstance(result, GenerateSentencesResponse)
    
    @pytest.mark.asyncio
    async def test_blacklist_raises_refused(self):
        """Should raise LlmRefused on blacklist finish reason."""
        client = GigaChatClient()
        client._token = TokenInfo(
            access_token="test_token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {"content": "Some content"},
                "finish_reason": "blacklist"
            }],
            "usage": {}
        }
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            with pytest.raises(LlmRefused):
                await client.chat_json(
                    messages=[{"role": "user", "content": "Generate"}],
                    validator=GenerateSentencesResponse,
                    temperature=0.7,
                    max_tokens=100,
                    timeout=10.0,
                    max_retries=0
                )
    
    @pytest.mark.asyncio
    async def test_validation_error_retries(self):
        """Should retry on Pydantic validation error."""
        client = GigaChatClient()
        client._token = TokenInfo(
            access_token="test_token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        # Mock invalid schema then valid
        mock_invalid_schema = MagicMock()
        mock_invalid_schema.status_code = 200
        mock_invalid_schema.json.return_value = {
            "choices": [{
                "message": {
                    "content": json.dumps({"wrong_field": "value"})
                },
                "finish_reason": "stop"
            }],
            "usage": {}
        }
        
        mock_valid = MagicMock()
        mock_valid.status_code = 200
        mock_valid.json.return_value = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "sentences": [{"english": "Test", "russian": "Тест"}]
                    })
                },
                "finish_reason": "stop"
            }],
            "usage": {}
        }
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = [mock_invalid_schema, mock_valid]
            
            result = await client.chat_json(
                messages=[{"role": "user", "content": "Generate"}],
                validator=GenerateSentencesResponse,
                temperature=0.7,
                max_tokens=100,
                timeout=10.0,
                max_retries=1
            )
            
            assert isinstance(result, GenerateSentencesResponse)


class TestJsonExtraction:
    """Tests for JSON extraction from text."""
    
    def test_extract_json_object(self):
        """Should extract JSON object from text."""
        client = GigaChatClient()
        
        text = 'Some text before {"key": "value"} and after'
        result = client._extract_json(text)
        
        assert result == '{"key": "value"}'
    
    def test_extract_json_array(self):
        """Should extract JSON array from text."""
        client = GigaChatClient()
        
        text = 'Text before [{"a": 1}, {"b": 2}] text after'
        result = client._extract_json(text)
        
        assert result == '[{"a": 1}, {"b": 2}]'
    
    def test_extract_json_from_markdown(self):
        """Should extract JSON from markdown code block."""
        client = GigaChatClient()
        
        text = '```json\n{"key": "value"}\n```'
        result = client._extract_json(text)
        
        assert result == '{"key": "value"}'
    
    def test_extract_nested_json(self):
        """Should extract nested JSON correctly."""
        client = GigaChatClient()
        
        text = '{"outer": {"inner": "value"}}'
        result = client._extract_json(text)
        
        assert result == '{"outer": {"inner": "value"}}'
    
    def test_no_json_found(self):
        """Should return None if no JSON found."""
        client = GigaChatClient()
        
        text = "No JSON here"
        result = client._extract_json(text)
        
        assert result is None

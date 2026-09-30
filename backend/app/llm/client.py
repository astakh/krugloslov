"""GigaChat client implementation."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import httpx
from pydantic import BaseModel, ValidationError

from app.config import settings
from app.llm.exceptions import (
    LlmError,
    LlmInvalidResponse,
    LlmQuotaExceeded,
    LlmRefused,
    LlmUnavailable,
)

logger = logging.getLogger(__name__)


class TokenInfo:
    """Stores GigaChat access token with expiration."""
    
    def __init__(self, access_token: str, expires_at: datetime):
        self.access_token = access_token
        self.expires_at = expires_at
    
    def is_expired(self) -> bool:
        """Check if token is expired or expires within 120 seconds."""
        now = datetime.now(timezone.utc)
        return now >= (self.expires_at - timedelta(seconds=120))


class GigaChatClient:
    """Client for GigaChat API with token management and retry logic."""
    
    OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    
    def __init__(self):
        self._token: TokenInfo | None = None
        self._token_lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(settings.GIGACHAT_MAX_CONCURRENCY)
        
        # SSL context
        self._ssl_context = None
        if settings.GIGACHAT_CA_CERT_PATH:
            import ssl
            self._ssl_context = ssl.create_default_context(
                cafile=settings.GIGACHAT_CA_CERT_PATH
            )
    
    async def _get_token(self) -> str:
        """Get valid access token, refreshing if needed."""
        async with self._token_lock:
            if self._token is None or self._token.is_expired():
                await self._refresh_token()
            return self._token.access_token
    
    async def _refresh_token(self) -> None:
        """Refresh OAuth token from GigaChat."""
        async with httpx.AsyncClient(verify=self._ssl_context or True) as client:
            try:
                response = await client.post(
                    self.OAUTH_URL,
                    headers={
                        "Authorization": f"Basic {settings.GIGACHAT_AUTH_KEY}",
                        "RqUID": str(uuid.uuid4()),
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={"scope": settings.GIGACHAT_SCOPE},
                    timeout=10.0,
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to get GigaChat token: {response.status_code}")
                    raise LlmUnavailable("Failed to authenticate with GigaChat")
                
                data = response.json()
                access_token = data["access_token"]
                expires_at = datetime.fromtimestamp(
                    data["expires_at"] / 1000,  # milliseconds to seconds
                    tz=timezone.utc
                )
                
                self._token = TokenInfo(access_token, expires_at)
                logger.info("GigaChat token refreshed successfully")
                
            except httpx.RequestError as e:
                logger.error(f"Network error during token refresh: {e}")
                raise LlmUnavailable("Failed to connect to GigaChat OAuth")
    
    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        timeout: float,
    ) -> dict[str, Any]:
        """
        Layer A: Send chat request to GigaChat.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds
        
        Returns:
            Response dict with 'content', 'finish_reason', 'usage'
        
        Raises:
            LlmUnavailable: Service unavailable after retries
            LlmQuotaExceeded: Quota exceeded
            LlmRefused: Content refused
        """
        token = await self._get_token()
        
        async with self._semaphore:
            async with httpx.AsyncClient(verify=self._ssl_context or True) as client:
                try:
                    response = await client.post(
                        self.CHAT_URL,
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": settings.GIGACHAT_MODEL,
                            "messages": messages,
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                        },
                        timeout=timeout,
                    )
                    
                    # Handle HTTP errors
                    if response.status_code == 401:
                        # Try refresh once
                        logger.warning("Got 401, refreshing token and retrying")
                        self._token = None
                        token = await self._get_token()
                        
                        response = await client.post(
                            self.CHAT_URL,
                            headers={
                                "Authorization": f"Bearer {token}",
                                "Content-Type": "application/json",
                            },
                            json={
                                "model": settings.GIGACHAT_MODEL,
                                "messages": messages,
                                "temperature": temperature,
                                "max_tokens": max_tokens,
                            },
                            timeout=timeout,
                        )
                        
                        if response.status_code == 401:
                            logger.error("Got 401 again after refresh")
                            raise LlmUnavailable("Authentication failed after refresh")
                    
                    elif response.status_code == 429:
                        # Rate limit - retry with backoff
                        retry_after = int(response.headers.get("Retry-After", 1))
                        logger.warning(f"Rate limited, waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                        
                        response = await client.post(
                            self.CHAT_URL,
                            headers={
                                "Authorization": f"Bearer {token}",
                                "Content-Type": "application/json",
                            },
                            json={
                                "model": settings.GIGACHAT_MODEL,
                                "messages": messages,
                                "temperature": temperature,
                                "max_tokens": max_tokens,
                            },
                            timeout=timeout,
                        )
                        
                        if response.status_code == 429:
                            raise LlmUnavailable("Rate limit exceeded after retry")
                    
                    elif response.status_code == 402:
                        logger.error("Quota exceeded (402)")
                        raise LlmQuotaExceeded("GigaChat quota exceeded")
                    
                    elif response.status_code == 400:
                        logger.error(f"Bad request: {response.text}")
                        raise LlmUnavailable(f"Bad request to GigaChat: {response.text}")
                    
                    elif response.status_code >= 500:
                        logger.error(f"Server error: {response.status_code}")
                        raise LlmUnavailable(f"GigaChat server error: {response.status_code}")
                    
                    elif response.status_code != 200:
                        logger.error(f"Unexpected status: {response.status_code}")
                        raise LlmUnavailable(f"Unexpected status: {response.status_code}")
                    
                    # Parse response
                    data = response.json()
                    choice = data["choices"][0]
                    message = choice["message"]
                    
                    return {
                        "content": message["content"],
                        "finish_reason": choice.get("finish_reason"),
                        "usage": data.get("usage", {}),
                    }
                
                except httpx.TimeoutException:
                    logger.error("Request timeout")
                    raise LlmUnavailable("Request timeout")
                
                except httpx.RequestError as e:
                    logger.error(f"Network error: {e}")
                    raise LlmUnavailable(f"Network error: {e}")
    
    async def chat_json(
        self,
        messages: list[dict[str, str]],
        validator: Callable[[dict], Any],
        temperature: float,
        max_tokens: int,
        timeout: float,
        max_retries: int = 2,
    ) -> Any:
        """
        Layer B: Send chat request and parse JSON response.
        
        Args:
            messages: List of message dicts
            validator: Pydantic model class for validation
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            timeout: Request timeout
            max_retries: Maximum retries on validation failure
        
        Returns:
            Validated Pydantic model instance
        
        Raises:
            LlmInvalidResponse: Failed to get valid JSON after retries
            LlmRefused: Content refused
        """
        for attempt in range(max_retries + 1):
            try:
                response = await self.chat(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout,
                )
                
                content = response["content"]
                finish_reason = response["finish_reason"]
                
                # Check finish reason
                if finish_reason == "blacklist":
                    logger.warning("Content refused by blacklist")
                    raise LlmRefused("Content refused by GigaChat")
                
                if finish_reason == "length":
                    logger.warning("Response truncated (length)")
                    if attempt < max_retries:
                        continue
                    raise LlmInvalidResponse("Response truncated")
                
                # Extract JSON from response
                json_str = self._extract_json(content)
                if not json_str:
                    logger.warning(f"Failed to extract JSON from: {content[:200]}")
                    if attempt < max_retries:
                        continue
                    raise LlmInvalidResponse("Failed to extract JSON from response")
                
                # Parse JSON
                try:
                    data = json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON parse error: {e}")
                    if attempt < max_retries:
                        continue
                    raise LlmInvalidResponse(f"JSON parse error: {e}")
                
                # Validate with Pydantic
                try:
                    return validator.model_validate(data)
                except ValidationError as e:
                    logger.warning(f"Validation error: {e}")
                    if attempt < max_retries:
                        continue
                    raise LlmInvalidResponse(f"Validation error: {e}")
                
            except (LlmUnavailable, LlmQuotaExceeded):
                # Don't retry these
                raise
            
            except LlmRefused:
                # Don't retry refused content
                raise
        
        raise LlmInvalidResponse("Failed to get valid response after retries")
    
    def _extract_json(self, text: str) -> str | None:
        """Extract JSON from text, handling markdown code blocks."""
        # Remove markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        
        text = text.strip()
        
        # Find JSON object or array
        start = -1
        for i, char in enumerate(text):
            if char in "{[":
                start = i
                break
        
        if start == -1:
            return None
        
        # Find matching closing bracket
        depth = 0
        end = -1
        for i in range(start, len(text)):
            if text[i] in "{[":
                depth += 1
            elif text[i] in "}]":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        
        if end == -1:
            return None
        
        return text[start:end]


# Global client instance
gigachat_client = GigaChatClient()

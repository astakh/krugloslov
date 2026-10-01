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
    CHAT_URL = "https://api.giga.chat/v1/chat/completions"
    
    def __init__(self):
        self._token: TokenInfo | None = None
        self._token_lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(settings.GIGACHAT_MAX_CONCURRENCY)
        
        # SSL verification - DISABLED for development
        # TODO: Enable for production with proper certificate
        self._verify_ssl = False
        logger.warning("⚠️  SSL verification DISABLED for GigaChat API (development mode)")
    
    async def _get_token(self) -> str:
        """Get valid access token, refreshing if needed."""
        async with self._token_lock:
            if self._token is None or self._token.is_expired():
                await self._refresh_token()
            return self._token.access_token
    
    async def _refresh_token(self) -> None:
        """Refresh OAuth token from GigaChat."""
        logger.info(f"Refreshing GigaChat token from {self.OAUTH_URL}")
        
        async with httpx.AsyncClient(verify=self._verify_ssl) as client:
            try:
                headers = {
                    "Authorization": f"Basic {settings.GIGACHAT_AUTH_KEY}",
                    "RqUID": str(uuid.uuid4()),
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                }
                
                logger.debug(f"OAuth request headers: Authorization=Basic ***{settings.GIGACHAT_AUTH_KEY[-10:]}, RqUID={headers['RqUID']}, scope={settings.GIGACHAT_SCOPE}")
                
                response = await client.post(
                    self.OAUTH_URL,
                    headers=headers,
                    data={"scope": settings.GIGACHAT_SCOPE},
                    timeout=float(settings.LLM_TOKEN_TIMEOUT),
                )
                
                logger.info(f"OAuth response status: {response.status_code}")
                
                if response.status_code != 200:
                    logger.error(f"Failed to get GigaChat token: {response.status_code}")
                    logger.error(f"Response body: {response.text}")
                    raise LlmUnavailable(f"Failed to authenticate with GigaChat: {response.status_code}")
                
                data = response.json()
                logger.debug(f"OAuth response data keys: {list(data.keys())}")
                
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
        
        # Use configured timeout or provided timeout, whichever is larger
        effective_timeout = max(timeout, settings.LLM_REQUEST_TIMEOUT)
        
        logger.info(f"Sending chat request to {self.CHAT_URL}")
        logger.debug(f"Request params: model={settings.GIGACHAT_MODEL}, temperature={temperature}, max_tokens={max_tokens}, timeout={effective_timeout}s")
        logger.debug(f"Messages count: {len(messages)}")
        
        async with self._semaphore:
            async with httpx.AsyncClient(verify=self._verify_ssl) as client:
                try:
                    request_data = {
                        "model": settings.GIGACHAT_MODEL,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "stream": False,
                    }
                    
                    logger.debug(f"Request payload: {json.dumps(request_data, ensure_ascii=False)[:500]}...")
                    
                    start_time = time.time()
                    response = await client.post(
                        self.CHAT_URL,
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json",
                            "Accept": "application/json",
                        },
                        json=request_data,
                        timeout=float(effective_timeout),
                    )
                    elapsed = time.time() - start_time
                    
                    logger.info(f"Chat response status: {response.status_code} (elapsed: {elapsed:.2f}s)")
                    
                    if response.status_code != 200:
                        logger.error(f"Chat API error: {response.status_code}")
                        logger.error(f"Response body: {response.text[:500]}")
                    
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
                
                # Log raw JSON string for debugging
                logger.info(f"Extracted JSON string (first 1000 chars): {json_str[:1000]}")
                
                # Parse JSON
                try:
                    data = json.loads(json_str)
                    logger.info(f"Successfully parsed JSON: {list(data.keys())}")
                except json.JSONDecodeError as e:
                    logger.error(f"JSON parse error: {e}")
                    logger.error(f"Error position: line {e.lineno}, column {e.colno}, char {e.pos}")
                    logger.error(f"Raw JSON string that failed to parse (full): {json_str}")
                    logger.error(f"Full LLM response content (full): {content}")
                    
                    # Show context around the error
                    error_pos = e.pos
                    context_start = max(0, error_pos - 50)
                    context_end = min(len(json_str), error_pos + 50)
                    logger.error(f"Context around error: ...{json_str[context_start:context_end]}...")
                    
                    # Try one more time with more aggressive fixes
                    try:
                        fixed_json = self._fix_common_json_issues(json_str)
                        logger.info(f"Attempting to parse fixed JSON (first 1000 chars): {fixed_json[:1000]}")
                        data = json.loads(fixed_json)
                        logger.info(f"Successfully parsed fixed JSON: {list(data.keys())}")
                    except json.JSONDecodeError as e2:
                        logger.error(f"Fixed JSON also failed to parse: {e2}")
                        logger.error(f"Fixed JSON error position: line {e2.lineno}, column {e2.colno}, char {e2.pos}")
                        if attempt < max_retries:
                            logger.info(f"Retrying LLM request (attempt {attempt + 2}/{max_retries + 1})")
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
    
    async def chat_json_raw(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        timeout: float,
        max_retries: int = 2,
    ) -> dict:
        """
        Send chat request and return raw JSON without validation.
        
        This method is useful when you need to adapt the response before validation.
        
        Args:
            messages: List of message dicts
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            timeout: Request timeout
            max_retries: Maximum retries on JSON extraction failure
        
        Returns:
            Raw JSON dict from LLM response
        
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
                    logger.debug(f"Extracted raw JSON: {data}")
                    return data
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON parse error: {e}")
                    if attempt < max_retries:
                        continue
                    raise LlmInvalidResponse(f"JSON parse error: {e}")
                
            except (LlmUnavailable, LlmQuotaExceeded):
                # Don't retry these
                raise
            
            except LlmRefused:
                # Don't retry refused content
                raise
        
        raise LlmInvalidResponse("Failed to get valid response after retries")
    
    def _extract_json(self, text: str) -> str | None:
        """Extract JSON from text, handling markdown code blocks and common issues."""
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
            logger.warning(f"No JSON object or array found in text: {text[:200]}")
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
            logger.warning(f"Unmatched brackets in JSON: {text[:200]}")
            return None
        
        json_str = text[start:end]
        
        # Try to fix common JSON issues
        json_str = self._fix_common_json_issues(json_str)
        
        return json_str
    
    def _fix_common_json_issues(self, json_str: str) -> str:
        """Attempt to fix common JSON formatting issues."""
        import re
        
        logger.info(f"Attempting to fix JSON issues in string (length: {len(json_str)})")
        
        # Fix missing quotes around keys (e.g., {key: "value"} -> {"key": "value"})
        json_str = re.sub(r'(?<=[{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r' "\1":', json_str)
        logger.debug(f"After fixing unquoted keys: {json_str[:200]}")
        
        # Fix single quotes to double quotes (but be careful not to break apostrophes in strings)
        # Only replace single quotes that are used as string delimiters
        json_str = re.sub(r"(?<=[\[{,])\s*'([^']*)'\s*(?=[\]},:])", r'"\1"', json_str)
        logger.debug(f"After fixing single quotes: {json_str[:200]}")
        
        # Fix trailing commas (e.g., {"a": 1,} -> {"a": 1})
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        logger.debug(f"After fixing trailing commas: {json_str[:200]}")
        
        # Fix missing colon (e.g., {"key" "value"} -> {"key": "value"})
        json_str = re.sub(r'"\s+"', '": "', json_str)
        logger.debug(f"After fixing missing colons: {json_str[:200]}")
        
        # Fix unescaped quotes inside strings
        # This is tricky, so we'll skip it for now
        
        logger.info(f"JSON fixing completed, final length: {len(json_str)}")
        
        return json_str


# Global client instance
gigachat_client = GigaChatClient()

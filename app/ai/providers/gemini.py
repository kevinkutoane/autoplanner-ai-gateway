"""Google Gemini REST API model provider implementation using httpx."""

import asyncio
import logging
import time
from typing import Optional
import httpx

from app.ai.providers.base import AIModelProvider, ProviderResult
from app.config import settings
from app.exceptions import (
    AIProviderError,
    AIServiceUnavailableError,
    RateLimitedError,
)

logger = logging.getLogger(__name__)


class GeminiModelProvider(AIModelProvider):
    """Async provider calling Google Gemini REST generateContent API."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(
        self,
        api_key: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
        max_retries: int = 2,
    ):
        self._api_key = api_key or settings.GEMINI_API_KEY
        self._client = client
        self._max_retries = max_retries

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        return httpx.AsyncClient(timeout=settings.UPSTREAM_TIMEOUT_SECONDS)

    async def generate(
        self,
        model: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        is_json: bool = False,
        request_id: Optional[str] = None,
    ) -> ProviderResult:
        if not self._api_key and not self._client:
            raise AIServiceUnavailableError(
                "Gemini API key is not configured on the gateway.",
                request_id=request_id,
            )

        endpoint = f"{self.BASE_URL}/{model}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self._api_key,
        }
        if request_id:
            headers["X-Request-ID"] = request_id

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ]
        }

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        if is_json:
            payload["generationConfig"] = {
                "responseMimeType": "application/json"
            }

        start_time = time.perf_counter()
        last_exception: Optional[Exception] = None

        for attempt in range(self._max_retries + 1):
            try:
                client = await self._get_client()
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers=headers,
                    timeout=settings.UPSTREAM_TIMEOUT_SECONDS,
                )

                elapsed_ms = int((time.perf_counter() - start_time) * 1000)

                # Upstream rate limit
                if response.status_code == 429:
                    if attempt < self._max_retries:
                        await asyncio.sleep(0.5 * (attempt + 1))
                        continue
                    raise RateLimitedError(
                        "Upstream Gemini API rate limit exceeded.",
                        request_id=request_id,
                    )

                # Upstream service unavailable or bad gateway
                if response.status_code in (502, 503, 504):
                    if attempt < self._max_retries:
                        await asyncio.sleep(0.5 * (attempt + 1))
                        continue
                    raise AIServiceUnavailableError(
                        "Upstream Gemini API is temporarily unavailable.",
                        request_id=request_id,
                    )

                # Upstream invalid request or unauthorized (do not retry)
                if response.status_code >= 400:
                    raise AIProviderError(
                        f"Upstream Gemini returned HTTP {response.status_code}.",
                        request_id=request_id,
                    )

                data = response.json()
                return self._parse_gemini_response(data, model, elapsed_ms, request_id)

            except httpx.TimeoutException as e:
                last_exception = e
                if attempt < self._max_retries:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                raise AIServiceUnavailableError(
                    "Upstream Gemini API request timed out.",
                    request_id=request_id,
                )
            except (RateLimitedError, AIServiceUnavailableError, AIProviderError):
                raise
            except Exception as e:
                last_exception = e
                if attempt < self._max_retries:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                raise AIProviderError(
                    f"Failed to communicate with AI provider: {type(e).__name__}",
                    request_id=request_id,
                )

        raise AIProviderError(
            f"Provider request failed: {last_exception}",
            request_id=request_id,
        )

    def _parse_gemini_response(
        self,
        data: dict,
        model: str,
        latency_ms: int,
        request_id: Optional[str],
    ) -> ProviderResult:
        candidates = data.get("candidates") or []
        if not candidates:
            raise AIProviderError(
                "Gemini returned an empty candidate list.",
                request_id=request_id,
            )

        first_candidate = candidates[0]
        content = first_candidate.get("content") or {}
        parts = content.get("parts") or []
        if not parts:
            raise AIProviderError(
                "Gemini returned candidate without parts.",
                request_id=request_id,
            )

        text = parts[0].get("text", "")
        usage = data.get("usageMetadata", {})
        prompt_tokens = usage.get("promptTokenCount", 0)
        completion_tokens = usage.get("candidatesTokenCount", 0)

        return ProviderResult(
            text=text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=model,
            latency_ms=latency_ms,
        )


# Default singleton instance
_default_gemini_provider: AIModelProvider = GeminiModelProvider()


def get_ai_provider() -> AIModelProvider:
    return _default_gemini_provider


def set_ai_provider(provider: AIModelProvider) -> None:
    global _default_gemini_provider
    _default_gemini_provider = provider

"""Tests for GeminiModelProvider with mocked HTTP transport."""

import pytest
import httpx
from app.ai.providers.gemini import GeminiModelProvider
from app.exceptions import (
    AIProviderError,
    AIServiceUnavailableError,
    RateLimitedError,
)


@pytest.mark.asyncio
async def test_gemini_provider_success():
    def handler(request: httpx.Request):
        assert request.headers["x-goog-api-key"] == "test-key"
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": "Hello from Gemini"}]
                        }
                    }
                ],
                "usageMetadata": {
                    "promptTokenCount": 25,
                    "candidatesTokenCount": 10,
                },
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = GeminiModelProvider(api_key="test-key", client=client, max_retries=0)
        res = await provider.generate(
            model="gemini-2.5-flash",
            prompt="Test prompt",
            request_id="req-p-1",
        )
        assert res.text == "Hello from Gemini"
        assert res.prompt_tokens == 25
        assert res.completion_tokens == 10
        assert res.model == "gemini-2.5-flash"
        assert res.latency_ms >= 0


@pytest.mark.asyncio
async def test_gemini_provider_429_rate_limit():
    def handler(request: httpx.Request):
        return httpx.Response(429, json={"error": "Resource exhausted"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = GeminiModelProvider(api_key="test-key", client=client, max_retries=0)
        with pytest.raises(RateLimitedError) as exc_info:
            await provider.generate(model="gemini-2.5-flash", prompt="Prompt")
        assert exc_info.value.status_code == 429
        assert "rate limit exceeded" in exc_info.value.message


@pytest.mark.asyncio
async def test_gemini_provider_503_service_unavailable():
    def handler(request: httpx.Request):
        return httpx.Response(503, text="Service Unavailable")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = GeminiModelProvider(api_key="test-key", client=client, max_retries=0)
        with pytest.raises(AIServiceUnavailableError) as exc_info:
            await provider.generate(model="gemini-2.5-flash", prompt="Prompt")
        assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_gemini_provider_timeout():
    def handler(request: httpx.Request):
        raise httpx.ReadTimeout("Timeout connecting to Gemini")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = GeminiModelProvider(api_key="test-key", client=client, max_retries=0)
        with pytest.raises(AIServiceUnavailableError) as exc_info:
            await provider.generate(model="gemini-2.5-flash", prompt="Prompt")
        assert exc_info.value.status_code == 503
        assert "timed out" in exc_info.value.message


@pytest.mark.asyncio
async def test_gemini_provider_missing_key_raises_unavailable():
    provider = GeminiModelProvider(api_key="", client=None)
    with pytest.raises(AIServiceUnavailableError) as exc_info:
        await provider.generate(model="gemini-2.5-flash", prompt="Prompt")
    assert "Gemini API key is not configured" in exc_info.value.message

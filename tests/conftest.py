"""Pytest configuration, fixtures, and provider mocks for AutoPlanner AI Gateway."""

import pytest
from typing import Optional
from fastapi.testclient import TestClient

from app.ai.providers.base import AIModelProvider, ProviderResult
from app.ai.providers.gemini import set_ai_provider
from app.config import settings
from app.main import app
from app.security.auth import AuthenticatedIdentity, IdentityProvider, set_identity_provider
from app.services.rate_limit import get_rate_limiter
from app.services.usage import get_usage_service


class MockAIProvider(AIModelProvider):
    """Mock provider for unit testing without invoking live external APIs."""

    def __init__(self, response_text: str = "Mocked AI completion"):
        self.response_text = response_text
        self.last_model: Optional[str] = None
        self.last_prompt: Optional[str] = None
        self.last_system_instruction: Optional[str] = None
        self.last_is_json: bool = False
        self.last_request_id: Optional[str] = None
        self.call_count: int = 0
        self.should_fail_with: Optional[Exception] = None

    async def generate(
        self,
        model: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        is_json: bool = False,
        request_id: Optional[str] = None,
    ) -> ProviderResult:
        self.call_count += 1
        self.last_model = model
        self.last_prompt = prompt
        self.last_system_instruction = system_instruction
        self.last_is_json = is_json
        self.last_request_id = request_id

        if self.should_fail_with:
            raise self.should_fail_with

        return ProviderResult(
            text=self.response_text,
            prompt_tokens=42,
            completion_tokens=18,
            model=model,
            latency_ms=120,
        )


@pytest.fixture(autouse=True)
def reset_gateway_state():
    """Reset settings, rate limiter, and usage buffer between tests."""
    settings.ENVIRONMENT = "development"
    settings.AUTH_REQUIRED = True
    settings.DEV_BEARER_TOKEN = "test-token"
    settings.API_KEYS = ["valid-api-key-1", "valid-api-key-2"]
    settings.FAST_MODEL = "gemini-2.5-flash"
    settings.PRO_MODEL = "gemini-2.5-pro"
    settings.RATE_LIMIT_RPM = 60

    limiter = get_rate_limiter()
    if hasattr(limiter, "reset"):
        import asyncio
        asyncio.run(limiter.reset())

    usage = get_usage_service()
    usage.clear()

    mock_provider = MockAIProvider()
    set_ai_provider(mock_provider)
    yield mock_provider


@pytest.fixture
def mock_provider(reset_gateway_state) -> MockAIProvider:
    return reset_gateway_state


@pytest.fixture
def client():
    """Synchronous test client for FastAPI endpoints."""
    with TestClient(app) as test_client:
        yield test_client

"""Core request orchestration service coordinating auth, rate limiting, routing, and telemetry."""

import logging
from typing import Optional

from app.ai.operations import AIOperation
from app.ai.prompts import PromptRegistry
from app.ai.providers.base import AIModelProvider
from app.ai.providers.gemini import get_ai_provider
from app.ai.router import ModelRouter, get_model_router
from app.ai.schemas import validate_operation_output
from app.exceptions import RateLimitedError
from app.models.requests import AIInvocationRequest
from app.models.responses import AIInvocationResponse
from app.security.auth import AuthenticatedIdentity
from app.services.rate_limit import RateLimiter, get_rate_limiter
from app.services.usage import UsageService, get_usage_service

logger = logging.getLogger(__name__)


class RequestService:
    """Coordinates incoming AI invocation requests through the entire gateway pipeline."""

    def __init__(
        self,
        ai_provider: Optional[AIModelProvider] = None,
        model_router: Optional[ModelRouter] = None,
        rate_limiter: Optional[RateLimiter] = None,
        usage_service: Optional[UsageService] = None,
    ):
        self._ai_provider = ai_provider
        self._model_router = model_router
        self._rate_limiter = rate_limiter
        self._usage_service = usage_service

    @property
    def ai_provider(self) -> AIModelProvider:
        return self._ai_provider or get_ai_provider()

    @property
    def model_router(self) -> ModelRouter:
        return self._model_router or get_model_router()

    @property
    def rate_limiter(self) -> RateLimiter:
        return self._rate_limiter or get_rate_limiter()

    @property
    def usage_service(self) -> UsageService:
        return self._usage_service or get_usage_service()

    async def execute_invocation(
        self,
        request: AIInvocationRequest,
        identity: AuthenticatedIdentity,
        correlation_id: str,
    ) -> AIInvocationResponse:
        """Executes the AI request through rate limiting, routing, generation, validation, and usage tracking."""
        # 1. Rate limiting check
        rate_key = identity.user_id if identity.is_authenticated else identity.client_id
        allowed, remaining, retry_after = await self.rate_limiter.is_allowed(rate_key)
        if not allowed:
            raise RateLimitedError(
                f"AI rate limit exceeded. Retry after {retry_after} seconds.",
                request_id=correlation_id,
            )

        # 2. Identify strongly-typed operation
        operation = request.typed_operation

        # 3. Retrieve server-owned prompt template
        prompt_template = PromptRegistry.get(operation)

        # 4. Construct prompt from structured inputs and context (ignoring client prompt string)
        prompt_text = prompt_template.build_prompt(request.input, request.context)

        # 5. Determine server-selected model
        selected_model = self.model_router.select_model(operation)

        # 6. Call upstream AI provider
        provider_result = await self.ai_provider.generate(
            model=selected_model,
            prompt=prompt_text,
            system_instruction=prompt_template.system_instruction,
            is_json=prompt_template.is_json,
            request_id=correlation_id,
        )

        # 7. Validate and normalize output (fail closed on malformed structured output)
        validated_text = validate_operation_output(operation, provider_result.text)

        # 8. Record safe operational usage telemetry (zero prompt/PII content)
        self.usage_service.record_invocation(
            request_id=correlation_id,
            operation=operation.value,
            model=provider_result.model,
            prompt_version=prompt_template.version,
            prompt_tokens=provider_result.prompt_tokens,
            completion_tokens=provider_result.completion_tokens,
            latency_ms=provider_result.latency_ms,
            success=True,
            user_id=identity.user_id,
            client_id=identity.client_id,
        )

        # 9. Return normalized response conforming to Flutter CloudAIProvider contract
        return AIInvocationResponse(
            text=validated_text,
            promptTokens=provider_result.prompt_tokens,
            completionTokens=provider_result.completion_tokens,
            model=provider_result.model,
        )


# Default singleton instance
_default_request_service = RequestService()


def get_request_service() -> RequestService:
    return _default_request_service


def set_request_service(service: RequestService) -> None:
    global _default_request_service
    _default_request_service = service

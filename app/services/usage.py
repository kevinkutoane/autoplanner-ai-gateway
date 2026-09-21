"""Usage and operational telemetry capture without logging user prompt text or PII."""

import logging
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("gateway.usage")


@dataclass(frozen=True)
class UsageRecord:
    """Safe structured telemetry record for an AI invocation."""

    requestId: str
    operation: str
    model: str
    promptVersion: str
    promptTokens: int
    completionTokens: int
    totalTokens: int
    latencyMs: int
    timestamp: str
    success: bool
    userId: Optional[str] = None
    clientId: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class UsageService:
    """Records operational invocation telemetry while strictly excluding prompts, context, and PII."""

    def __init__(self):
        # In-memory buffer for diagnostics and testing
        self._history: List[UsageRecord] = []

    def record_invocation(
        self,
        request_id: str,
        operation: str,
        model: str,
        prompt_version: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: int,
        success: bool = True,
        user_id: Optional[str] = None,
        client_id: Optional[str] = None,
    ) -> UsageRecord:
        """Captures safe operational metrics and logs structured telemetry."""
        record = UsageRecord(
            requestId=request_id,
            operation=operation,
            model=model,
            promptVersion=prompt_version,
            promptTokens=max(0, prompt_tokens),
            completionTokens=max(0, completion_tokens),
            totalTokens=max(0, prompt_tokens + completion_tokens),
            latencyMs=max(0, latency_ms),
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            success=success,
            userId=user_id,
            clientId=client_id,
        )

        self._history.append(record)
        # Cap in-memory history to avoid unbounded memory growth
        if len(self._history) > 1000:
            self._history.pop(0)

        # Emit structured log containing ONLY operational metadata — never prompts or user content
        logger.info(
            "AI invocation completed",
            extra={
                "telemetry": record.to_dict(),
            },
        )
        return record

    @property
    def history(self) -> List[UsageRecord]:
        return list(self._history)

    def clear(self) -> None:
        self._history.clear()


# Default singleton instance
_default_usage_service = UsageService()


def get_usage_service() -> UsageService:
    return _default_usage_service


def set_usage_service(service: UsageService) -> None:
    global _default_usage_service
    _default_usage_service = service

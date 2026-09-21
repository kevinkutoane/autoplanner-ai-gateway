"""Abstract base class and response types for AI model providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ProviderResult:
    """Normalized output from an underlying AI model provider."""

    text: str
    prompt_tokens: int
    completion_tokens: int
    model: str
    latency_ms: int


class AIModelProvider(ABC):
    """Provider-agnostic interface for invoking upstream large language models."""

    @abstractmethod
    async def generate(
        self,
        model: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        is_json: bool = False,
        request_id: Optional[str] = None,
    ) -> ProviderResult:
        """Invokes the model and returns normalized generation text and token counts."""
        pass

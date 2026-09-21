"""Model router mapping semantic operations to configured Gemini models."""

from typing import Dict
from app.ai.operations import AIOperation
from app.config import settings


class ModelRouter:
    """Server-side model router deciding the underlying Gemini model tier.

    Clients cannot choose or override the model.
    """

    def __init__(self, fast_model: str = None, pro_model: str = None):
        self._fast_model = fast_model or settings.FAST_MODEL
        self._pro_model = pro_model or settings.PRO_MODEL

    def select_model(self, operation: AIOperation) -> str:
        """Deterministically selects the configured model for an operation."""
        # Complex multi-entity synthesis and in-depth reasoning use PRO_MODEL
        if operation in {
            AIOperation.BRAIN_DUMP,
            AIOperation.PLAN_DAY,
            AIOperation.WEEKLY_REVIEW,
            AIOperation.CHAT_COACH,
        }:
            return self._pro_model

        # Fast parsing, tagging, and slot selection use FAST_MODEL
        return self._fast_model


# Default singleton instance
_default_model_router = ModelRouter()


def get_model_router() -> ModelRouter:
    return _default_model_router


def set_model_router(router: ModelRouter) -> None:
    global _default_model_router
    _default_model_router = router

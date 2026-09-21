"""Pydantic models for incoming AI gateway requests."""

import json
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_validator

from app.ai.operations import AIOperation
from app.config import settings


class AIInvocationRequest(BaseModel):
    """Wire representation of an AI invocation matching Flutter's AIInvocation.toJson()."""

    id: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Unique request / invocation ID for correlation and deduplication",
    )
    operation: str = Field(
        ...,
        description="Wire name of the semantic AI operation",
    )
    input: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured input payload specific to the operation",
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Contextual metadata (e.g. memories, work hours, existing items)",
    )
    client: Dict[str, Any] = Field(
        default_factory=dict,
        description="Client telemetry such as appVersion, platform, etc.",
    )
    timestamp: Optional[str] = Field(
        default=None,
        description="ISO-8601 creation timestamp",
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Invocation id must not be empty or whitespace.")
        return clean

    @field_validator("operation")
    @classmethod
    def validate_operation(cls, v: str) -> str:
        op = AIOperation.from_str(v)
        if op is None:
            raise ValueError(f"Unknown or unsupported operation: '{v}'.")
        return op.value

    @field_validator("input")
    @classmethod
    def validate_input_size(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        # Validate individual string field lengths
        for key, val in v.items():
            if isinstance(val, str) and len(val) > settings.MAX_INPUT_TEXT_CHARS:
                raise ValueError(
                    f"Input field '{key}' exceeds maximum allowed length of "
                    f"{settings.MAX_INPUT_TEXT_CHARS} characters."
                )
        return v

    @field_validator("context")
    @classmethod
    def validate_context_size(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        try:
            serialized = json.dumps(v)
            if len(serialized.encode("utf-8")) > settings.MAX_CONTEXT_SERIALIZED_BYTES:
                raise ValueError(
                    f"Context payload exceeds maximum size of "
                    f"{settings.MAX_CONTEXT_SERIALIZED_BYTES} bytes."
                )
        except (TypeError, OverflowError) as e:
            raise ValueError(f"Invalid context structure: {e}")
        return v

    @property
    def typed_operation(self) -> AIOperation:
        """Return strongly typed AIOperation enum."""
        op = AIOperation.from_str(self.operation)
        if not op:
            raise ValueError(f"Invalid operation '{self.operation}'.")
        return op

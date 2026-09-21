"""JSON schemas and output validation for structured AI operations."""

import json
from typing import Any, Dict, List, Optional
from app.ai.operations import AIOperation
from app.exceptions import AIProviderError


def validate_operation_output(operation: AIOperation, raw_text: str) -> str:
    """Validates that raw AI output conforms structurally to the expected operation contract.

    Returns the cleaned raw_text if valid, or raises AIProviderError if structurally invalid.
    """
    if not operation.is_structured_json:
        return raw_text.strip()

    # Extract JSON if model wrapped it in markdown code fences
    cleaned = _extract_json_text(raw_text)

    try:
        data = json.loads(cleaned)
    except Exception as e:
        raise AIProviderError(f"Model response was not valid JSON for operation '{operation.value}': {e}")

    # Specific structural checks
    if operation == AIOperation.PARSE_TASKS:
        if not isinstance(data, list):
            raise AIProviderError("Expected JSON array of tasks for parse_tasks.")
        for item in data:
            if not isinstance(item, dict) or "title" not in item:
                raise AIProviderError("Invalid task entry in parse_tasks: missing 'title'.")

    elif operation == AIOperation.BRAIN_DUMP:
        if not isinstance(data, dict):
            raise AIProviderError("Expected JSON object with tasks, notes, goals, memories for brain_dump.")
        for key in ("tasks", "notes", "goals", "memories"):
            if key in data and not isinstance(data[key], list):
                raise AIProviderError(f"Field '{key}' in brain_dump output must be an array.")

    elif operation == AIOperation.PLAN_DAY:
        if not isinstance(data, list):
            raise AIProviderError("Expected JSON array of planned tasks for plan_day.")

    elif operation == AIOperation.GENERATE_TAGS:
        if not isinstance(data, list) or not all(isinstance(t, str) for t in data):
            raise AIProviderError("Expected JSON array of string tags for generate_tags.")

    elif operation == AIOperation.SUGGEST_TASKS:
        if not isinstance(data, list):
            raise AIProviderError("Expected JSON array of task title suggestions for suggest_tasks.")

    elif operation == AIOperation.EXTRACT_PATTERNS:
        if not isinstance(data, list):
            raise AIProviderError("Expected JSON array of patterns for extract_patterns.")

    elif operation == AIOperation.PARSE_SCHEDULE_COMMAND:
        if not isinstance(data, dict) or "action" not in data:
            raise AIProviderError("Expected JSON object with 'action' for parse_schedule_command.")

    return cleaned


def _extract_json_text(text: str) -> str:
    """Strips markdown ```json ... ``` code fences if present."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        # Drop first line (``` or ```json)
        if len(lines) > 1 and lines[0].startswith("```"):
            lines = lines[1:]
        # Drop last line if ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return stripped

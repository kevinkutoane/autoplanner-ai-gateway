"""Tests certifying all 13 semantic AI operations in the registry."""

import pytest
from app.ai.operations import AIOperation
from app.ai.prompts import PromptRegistry
from app.ai.router import ModelRouter
from app.config import settings

EXPECTED_OPERATIONS = [
    "brain_dump",
    "parse_tasks",
    "plan_day",
    "chat_coach",
    "daily_insight",
    "suggest_reschedule",
    "summarize_note",
    "generate_tags",
    "extract_memory",
    "extract_patterns",
    "suggest_tasks",
    "weekly_review",
    "parse_schedule_command",
]


def test_all_13_operations_exist_in_enum():
    wire_names = [op.value for op in AIOperation]
    for expected in EXPECTED_OPERATIONS:
        assert expected in wire_names, f"Operation {expected} missing from AIOperation"
    assert len(AIOperation) == 13


@pytest.mark.parametrize("wire_name", EXPECTED_OPERATIONS)
def test_all_operations_registered_in_prompt_registry(wire_name: str):
    op = AIOperation.from_str(wire_name)
    assert op is not None

    template = PromptRegistry.get(op)
    assert template is not None
    assert template.operation == op
    assert template.version.startswith(f"{wire_name}:")
    assert len(template.system_instruction) > 0

    # Verify building prompt with dummy data works without throwing
    prompt_str = template.build_prompt({"text": "Hello world", "content": "Sample content"}, {"memories": []})
    assert len(prompt_str) > 0


@pytest.mark.parametrize("wire_name", EXPECTED_OPERATIONS)
def test_all_operations_have_model_route(wire_name: str):
    op = AIOperation.from_str(wire_name)
    router = ModelRouter(fast_model="fast-m", pro_model="pro-m")
    selected = router.select_model(op)
    assert selected in ("fast-m", "pro-m")

"""Tests certifying server prompt ownership and independence from client prompt strings."""

from fastapi.testclient import TestClient
from app.ai.operations import AIOperation
from app.ai.prompts import PromptRegistry


def test_server_owns_prompt_generation_ignoring_client_prompt(client: TestClient, mock_provider):
    mock_provider.response_text = '[{"title": "Clean desk"}]'

    # Client passes a custom/stale prompt in input
    payload = {
        "id": "req-prompt-1",
        "operation": "parse_tasks",
        "input": {
            "text": "Clean desk tomorrow at 9am",
            "prompt": "OLD CLIENT PROMPT THAT MUST BE IGNORED",
        },
        "context": {"memories": []},
    }

    response = client.post(
        "/v1/ai/complete",
        json=payload,
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 200

    # Verify that what reached the mock provider is the server's authoritative template
    assert mock_provider.last_prompt is not None
    assert "OLD CLIENT PROMPT THAT MUST BE IGNORED" not in mock_provider.last_prompt
    assert "Extract all actionable tasks" in mock_provider.last_prompt
    assert "Clean desk tomorrow at 9am" in mock_provider.last_prompt


def test_operation_succeeds_when_client_prompt_is_absent(client: TestClient, mock_provider):
    mock_provider.response_text = '[{"title": "Read book"}]'

    payload = {
        "id": "req-prompt-2",
        "operation": "parse_tasks",
        "input": {
            "text": "Read book tonight",
        },
    }

    response = client.post(
        "/v1/ai/complete",
        json=payload,
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 200
    assert mock_provider.last_prompt is not None
    assert "Read book tonight" in mock_provider.last_prompt


def test_prompt_registry_versions_are_explicit():
    for op in AIOperation:
        template = PromptRegistry.get(op)
        assert ":v" in template.version

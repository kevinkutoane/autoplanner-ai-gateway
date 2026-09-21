"""Tests for structured output schema validation and markdown code fence extraction."""

from fastapi.testclient import TestClient
from app.ai.operations import AIOperation
from app.ai.schemas import validate_operation_output
from app.exceptions import AIProviderError
import pytest


def test_markdown_fence_stripping():
    raw_markdown = "```json\n[{\"title\": \"Task from markdown\"}]\n```"
    cleaned = validate_operation_output(AIOperation.PARSE_TASKS, raw_markdown)
    assert cleaned == '[{"title": "Task from markdown"}]'


def test_malformed_json_raises_provider_error(client: TestClient, mock_provider):
    # Provider returns truncated/malformed JSON
    mock_provider.response_text = "[{\"title\": \"Broken JSON"

    payload = {
        "id": "req-struct-1",
        "operation": "parse_tasks",
        "input": {"text": "Buy milk"},
    }

    response = client.post(
        "/v1/ai/complete",
        json=payload,
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 502
    data = response.json()
    assert data["error"]["code"] == "AI_PROVIDER_ERROR"
    assert "not valid JSON" in data["error"]["message"]


def test_wrong_json_structure_fails_closed(client: TestClient, mock_provider):
    # parse_tasks expects a JSON array, but provider returned a JSON object
    mock_provider.response_text = '{"status": "not an array"}'

    payload = {
        "id": "req-struct-2",
        "operation": "parse_tasks",
        "input": {"text": "Buy milk"},
    }

    response = client.post(
        "/v1/ai/complete",
        json=payload,
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 502
    assert "Expected JSON array" in response.json()["error"]["message"]

"""Tests for server-side model selection and routing determinism."""

from fastapi.testclient import TestClient
from app.ai.operations import AIOperation
from app.ai.router import ModelRouter
from app.config import settings


def test_model_routing_is_deterministic():
    router = ModelRouter(fast_model="custom-fast", pro_model="custom-pro")
    assert router.select_model(AIOperation.PARSE_TASKS) == "custom-fast"
    assert router.select_model(AIOperation.BRAIN_DUMP) == "custom-pro"
    assert router.select_model(AIOperation.PLAN_DAY) == "custom-pro"
    assert router.select_model(AIOperation.WEEKLY_REVIEW) == "custom-pro"
    assert router.select_model(AIOperation.CHAT_COACH) == "custom-pro"
    assert router.select_model(AIOperation.GENERATE_TAGS) == "custom-fast"
    assert router.select_model(AIOperation.DAILY_INSIGHT) == "custom-fast"


def test_client_cannot_override_model(client: TestClient, mock_provider):
    mock_provider.response_text = '[{"title": "Task"}]'

    # Client attempts to request a different model in payload or headers
    payload = {
        "id": "req-route-1",
        "operation": "parse_tasks",
        "input": {"text": "Buy groceries"},
        "model": "client-injected-expensive-model",
    }

    response = client.post(
        "/v1/ai/complete",
        json=payload,
        headers={
            "Authorization": "Bearer test-token",
            "X-Model": "gemini-ultra-custom",
        },
    )
    assert response.status_code == 200
    # Server selected fast model must be used
    assert response.json()["model"] == settings.FAST_MODEL
    assert mock_provider.last_model == settings.FAST_MODEL

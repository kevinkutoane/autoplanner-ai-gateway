"""Tests for authentication boundary."""

from fastapi.testclient import TestClient
from app.config import settings


def test_auth_missing_token_returns_401(client: TestClient):
    payload = {
        "id": "req-1",
        "operation": "parse_tasks",
        "input": {"text": "Buy milk"},
    }
    response = client.post("/v1/ai/complete", json=payload)
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "UNAUTHENTICATED"
    assert "Missing Authorization" in data["error"]["message"]


def test_auth_malformed_header_returns_401(client: TestClient):
    payload = {
        "id": "req-2",
        "operation": "parse_tasks",
        "input": {"text": "Buy milk"},
    }
    # Missing 'Bearer ' prefix
    response = client.post(
        "/v1/ai/complete",
        json=payload,
        headers={"Authorization": "Basic 12345"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_auth_invalid_token_returns_401(client: TestClient):
    payload = {
        "id": "req-3",
        "operation": "parse_tasks",
        "input": {"text": "Buy milk"},
    }
    response = client.post(
        "/v1/ai/complete",
        json=payload,
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_auth_valid_dev_token_succeeds(client: TestClient, mock_provider):
    mock_provider.response_text = '[{"title": "Task 1"}]'
    payload = {
        "id": "req-4",
        "operation": "parse_tasks",
        "input": {"text": "Buy milk"},
    }
    response = client.post(
        "/v1/ai/complete",
        json=payload,
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 200
    assert response.json()["model"] == settings.FAST_MODEL


def test_auth_valid_api_key_succeeds(client: TestClient, mock_provider):
    mock_provider.response_text = '[{"title": "Task 1"}]'
    payload = {
        "id": "req-5",
        "operation": "parse_tasks",
        "input": {"text": "Buy milk"},
    }
    response = client.post(
        "/v1/ai/complete",
        json=payload,
        headers={"Authorization": "Bearer valid-api-key-1"},
    )
    assert response.status_code == 200


def test_auth_dev_anonymous_permitted_only_when_auth_required_false(client: TestClient, mock_provider):
    settings.AUTH_REQUIRED = False
    settings.ENVIRONMENT = "development"
    mock_provider.response_text = '[{"title": "Task 1"}]'

    payload = {
        "id": "req-6",
        "operation": "parse_tasks",
        "input": {"text": "Buy milk"},
    }
    response = client.post("/v1/ai/complete", json=payload)
    assert response.status_code == 200


def test_auth_production_enforces_auth_even_if_flag_is_false(client: TestClient):
    settings.AUTH_REQUIRED = False
    settings.ENVIRONMENT = "production"

    payload = {
        "id": "req-7",
        "operation": "parse_tasks",
        "input": {"text": "Buy milk"},
    }
    response = client.post("/v1/ai/complete", json=payload)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"

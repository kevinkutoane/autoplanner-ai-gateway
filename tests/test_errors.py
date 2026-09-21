"""Tests certifying canonical error envelope normalization across status codes."""

import pytest
from fastapi.testclient import TestClient
from app.exceptions import AIProviderError, AIServiceUnavailableError, InternalError
from app.main import app



def test_404_not_found_envelope(client: TestClient):
    response = client.get("/v1/unknown-route")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
    assert "requestId" in data["error"]


def test_502_provider_error_envelope(client: TestClient, mock_provider):
    mock_provider.should_fail_with = AIProviderError("Simulated upstream provider breakdown")

    response = client.post(
        "/v1/ai/complete",
        json={"id": "req-err-502", "operation": "daily_insight", "input": {}},
        headers={"Authorization": "Bearer test-token", "X-Request-ID": "req-err-502"},
    )
    assert response.status_code == 502
    data = response.json()
    assert data["error"]["code"] == "AI_PROVIDER_ERROR"
    assert data["error"]["requestId"] == "req-err-502"
    assert response.headers.get("X-Request-ID") == "req-err-502"


def test_503_service_unavailable_envelope(client: TestClient, mock_provider):
    mock_provider.should_fail_with = AIServiceUnavailableError("Gateway connection timed out")

    response = client.post(
        "/v1/ai/complete",
        json={"id": "req-err-503", "operation": "daily_insight", "input": {}},
        headers={"Authorization": "Bearer test-token", "X-Request-ID": "req-err-503"},
    )
    assert response.status_code == 503
    data = response.json()
    assert data["error"]["code"] == "AI_SERVICE_UNAVAILABLE"
    assert data["error"]["requestId"] == "req-err-503"


def test_500_internal_error_does_not_leak_stack_trace(mock_provider):
    mock_provider.should_fail_with = RuntimeError("Unexpected zero division or crash inside service")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/v1/ai/complete",
            json={"id": "req-err-500", "operation": "daily_insight", "input": {}},
            headers={"Authorization": "Bearer test-token", "X-Request-ID": "req-err-500"},
        )
        assert response.status_code == 500
        data = response.json()
        assert data["error"]["code"] == "INTERNAL_ERROR"
        # Verify no raw traceback leaked in error message
        assert "Traceback" not in data["error"]["message"]
        assert "RuntimeError" not in data["error"]["message"]


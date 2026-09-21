"""Tests for usage telemetry capture and zero-leakage privacy guarantees."""

from fastapi.testclient import TestClient
from app.services.usage import get_usage_service


def test_telemetry_recorded_on_success(client: TestClient, mock_provider):
    mock_provider.response_text = "Supportive coach response"
    usage = get_usage_service()
    usage.clear()

    payload = {
        "id": "req-telemetry-1",
        "operation": "chat_coach",
        "input": {"message": "SENSITIVE_USER_MESSAGE_NEVER_LOG_ME"},
        "context": {"secret_context": "CONFIDENTIAL_CONTEXT"},
    }

    response = client.post(
        "/v1/ai/complete",
        json=payload,
        headers={
            "Authorization": "Bearer test-token",
            "X-Request-ID": "req-telemetry-1",
        },
    )
    assert response.status_code == 200

    history = usage.history
    assert len(history) == 1
    record = history[0]

    assert record.requestId == "req-telemetry-1"
    assert record.operation == "chat_coach"
    assert record.promptVersion == "chat_coach:v1"
    assert record.promptTokens == 42
    assert record.completionTokens == 18
    assert record.totalTokens == 60
    assert record.success is True

    # Strict Privacy Check: Verify sensitive user content is nowhere in the telemetry record dictionary
    record_dict = record.to_dict()
    record_str = str(record_dict)
    assert "SENSITIVE_USER_MESSAGE_NEVER_LOG_ME" not in record_str
    assert "CONFIDENTIAL_CONTEXT" not in record_str
    assert "Supportive coach response" not in record_str

"""Tests for incoming request validation and bounds checking."""

import pytest
from fastapi.testclient import TestClient
from app.config import settings


def test_validation_missing_id_fails_400(client: TestClient):
    payload = {
        "operation": "parse_tasks",
        "input": {"text": "Buy milk"},
    }
    response = client.post(
        "/v1/ai/complete",
        json=payload,
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "INVALID_REQUEST"


def test_validation_empty_id_fails_400(client: TestClient):
    payload = {
        "id": "   ",
        "operation": "parse_tasks",
        "input": {"text": "Buy milk"},
    }
    response = client.post(
        "/v1/ai/complete",
        json=payload,
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 400
    assert "Invocation id must not be empty" in response.json()["error"]["message"]


def test_validation_missing_operation_fails_400(client: TestClient):
    payload = {
        "id": "req-val-1",
        "input": {"text": "Buy milk"},
    }
    response = client.post(
        "/v1/ai/complete",
        json=payload,
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_validation_unknown_operation_fails_closed_400(client: TestClient):
    payload = {
        "id": "req-val-2",
        "operation": "unsupported_hack_op",
        "input": {"text": "Buy milk"},
    }
    response = client.post(
        "/v1/ai/complete",
        json=payload,
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "INVALID_REQUEST"
    assert "Unknown or unsupported operation" in data["error"]["message"]


def test_validation_oversized_input_text_fails_400(client: TestClient):
    payload = {
        "id": "req-val-3",
        "operation": "parse_tasks",
        "input": {"text": "A" * (settings.MAX_INPUT_TEXT_CHARS + 10)},
    }
    response = client.post(
        "/v1/ai/complete",
        json=payload,
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 400
    assert "exceeds maximum allowed length" in response.json()["error"]["message"]


def test_validation_oversized_context_fails_400(client: TestClient):
    payload = {
        "id": "req-val-4",
        "operation": "parse_tasks",
        "input": {"text": "Buy milk"},
        "context": {"heavy_data": "x" * (settings.MAX_CONTEXT_SERIALIZED_BYTES + 50)},
    }
    response = client.post(
        "/v1/ai/complete",
        json=payload,
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 400
    assert "Context payload exceeds maximum size" in response.json()["error"]["message"]


def test_validation_oversized_payload_returns_413(client: TestClient):
    # Simulated content-length over MAX_REQUEST_BYTES
    oversized_length = str(settings.MAX_REQUEST_BYTES + 1000)
    response = client.post(
        "/v1/ai/complete",
        content=b"{}",
        headers={
            "Authorization": "Bearer test-token",
            "Content-Type": "application/json",
            "Content-Length": oversized_length,
        },
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"

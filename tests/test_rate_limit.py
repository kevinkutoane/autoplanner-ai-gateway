"""Tests for rate limiting enforcement and client isolation."""

import pytest
from fastapi.testclient import TestClient
from app.config import settings
from app.services.rate_limit import InMemoryRateLimiter, set_rate_limiter


def test_rate_limiting_enforced(client: TestClient, mock_provider):
    mock_provider.response_text = "Daily tip"

    # Set tight rate limit of 2 RPM for testing
    test_limiter = InMemoryRateLimiter(limit_rpm=2, window_seconds=60)
    set_rate_limiter(test_limiter)

    payload = {
        "id": "req-rl-1",
        "operation": "daily_insight",
        "input": {},
    }

    # Request 1: succeeds
    res1 = client.post("/v1/ai/complete", json=payload, headers={"Authorization": "Bearer test-token"})
    assert res1.status_code == 200

    # Request 2: succeeds
    payload["id"] = "req-rl-2"
    res2 = client.post("/v1/ai/complete", json=payload, headers={"Authorization": "Bearer test-token"})
    assert res2.status_code == 200

    # Request 3: blocked with 429
    payload["id"] = "req-rl-3"
    res3 = client.post("/v1/ai/complete", json=payload, headers={"Authorization": "Bearer test-token"})
    assert res3.status_code == 429
    assert res3.json()["error"]["code"] == "RATE_LIMITED"


def test_rate_limiting_client_isolation(client: TestClient, mock_provider):
    mock_provider.response_text = "Daily tip"

    test_limiter = InMemoryRateLimiter(limit_rpm=1, window_seconds=60)
    set_rate_limiter(test_limiter)

    # Client 1 exhausts quota
    res1 = client.post(
        "/v1/ai/complete",
        json={"id": "req-c1", "operation": "daily_insight", "input": {}},
        headers={"Authorization": "Bearer valid-api-key-1"},
    )
    assert res1.status_code == 200

    res1_blocked = client.post(
        "/v1/ai/complete",
        json={"id": "req-c1-2", "operation": "daily_insight", "input": {}},
        headers={"Authorization": "Bearer valid-api-key-1"},
    )
    assert res1_blocked.status_code == 429

    # Client 2 should still be allowed
    res2 = client.post(
        "/v1/ai/complete",
        json={"id": "req-c2", "operation": "daily_insight", "input": {}},
        headers={"Authorization": "Bearer valid-api-key-2"},
    )
    assert res2.status_code == 200

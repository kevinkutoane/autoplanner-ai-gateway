"""Tests for /health endpoint."""

from fastapi.testclient import TestClient
from app.config import settings


def test_health_success(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == settings.GATEWAY_VERSION
    assert "timestamp" in data
    assert "T" in data["timestamp"]


def test_health_does_not_leak_secrets(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    text = response.text
    assert "gemini" not in text.lower()
    assert "api_key" not in text.lower()
    assert "secret" not in text.lower()

"""API endpoint tests."""

import pytest


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_list_themes_empty(client):
    """Test themes endpoint with no data."""
    response = client.get("/themes")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_search_empty(client):
    """Test search endpoint with no data."""
    response = client.get("/search?q=test")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_admin_config(client):
    """Test admin config endpoint."""
    response = client.get("/admin/config")
    assert response.status_code == 200
    data = response.json()
    assert "weights" in data
    assert "segment_priorities" in data


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "ProduckAI API"
    assert "version" in data

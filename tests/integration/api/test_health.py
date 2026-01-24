"""
Integration tests for the health check endpoint.

Tests:
    - GET /health returns 200 with healthy status
"""


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_check_returns_200(self, client):
        """Test that health check endpoint returns 200 OK."""
        response = client.get("/health")

        assert response.status_code == 200

    def test_health_check_returns_healthy_status(self, client):
        """Test that health check returns healthy status in response body."""
        response = client.get("/health")
        data = response.json()

        assert data["status"] == "healthy"

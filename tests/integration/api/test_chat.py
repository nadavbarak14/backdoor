"""
Integration tests for the chat streaming endpoint.

Tests:
    - POST /api/v1/chat/stream returns SSE stream
    - Response format is compatible with Vercel AI SDK
    - Error handling for invalid requests
"""

from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest


class MockChatService:
    """Mock chat service for testing without real LLM calls."""

    def __init__(self):
        self.sessions = {}
        self.tools = []

    async def stream(
        self,
        messages: list,
        session_id: str,
    ) -> AsyncGenerator[str, None]:
        """Mock stream that yields test response."""
        # Get the last user message for echoing
        last_user_message = ""
        for msg in reversed(messages):
            if msg.role == "user":
                last_user_message = msg.content
                break

        # Yield a mock response word by word
        response = f"Mock response to: {last_user_message}"
        for word in response.split():
            yield word + " "

    def clear_session(self, session_id: str) -> bool:
        return session_id in self.sessions


@pytest.fixture
def mock_chat_service():
    """Fixture to mock the chat service."""
    mock_service = MockChatService()
    with patch("src.api.v1.chat.get_chat_service", return_value=mock_service):
        yield mock_service


class TestChatStream:
    """Tests for the chat streaming endpoint."""

    def test_chat_stream_returns_200(self, client, mock_chat_service):
        """Test that chat stream endpoint returns 200 OK."""
        response = client.post(
            "/api/v1/chat/stream",
            json={"messages": [{"role": "user", "content": "Hello"}]},
        )

        assert response.status_code == 200

    def test_chat_stream_returns_correct_content_type(self, client, mock_chat_service):
        """Test that chat stream returns text/plain content type for Vercel AI SDK."""
        response = client.post(
            "/api/v1/chat/stream",
            json={"messages": [{"role": "user", "content": "Hello"}]},
        )

        assert response.headers["content-type"] == "text/plain; charset=utf-8"

    def test_chat_stream_has_correct_headers(self, client, mock_chat_service):
        """Test that chat stream has proper SSE headers."""
        response = client.post(
            "/api/v1/chat/stream",
            json={"messages": [{"role": "user", "content": "Hello"}]},
        )

        assert response.headers["cache-control"] == "no-cache"

    def test_chat_stream_returns_data_chunks(self, client, mock_chat_service):
        """Test that chat stream returns Vercel AI SDK format chunks (0: prefix)."""
        response = client.post(
            "/api/v1/chat/stream",
            json={"messages": [{"role": "user", "content": "Hello"}]},
        )

        content = response.text
        # Should contain 0: prefixed lines (Vercel AI SDK Data Stream Protocol)
        assert '0:"' in content

    def test_chat_stream_ends_with_done(self, client, mock_chat_service):
        """Test that chat stream ends with done signal (d: prefix)."""
        response = client.post(
            "/api/v1/chat/stream",
            json={"messages": [{"role": "user", "content": "Hello"}]},
        )

        content = response.text
        # Vercel AI SDK uses d: for done signal
        assert 'd:{"finishReason"' in content

    def test_chat_stream_echoes_user_message(self, client, mock_chat_service):
        """Test that response includes user message context."""
        response = client.post(
            "/api/v1/chat/stream",
            json={"messages": [{"role": "user", "content": "test message"}]},
        )

        content = response.text
        # Mock response should include the user message
        assert "test" in content or "message" in content

    def test_chat_stream_with_system_message(self, client, mock_chat_service):
        """Test that chat stream accepts system messages."""
        response = client.post(
            "/api/v1/chat/stream",
            json={
                "messages": [
                    {"role": "system", "content": "You are helpful."},
                    {"role": "user", "content": "Hello"},
                ]
            },
        )

        assert response.status_code == 200

    def test_chat_stream_with_conversation_history(self, client, mock_chat_service):
        """Test that chat stream accepts conversation history."""
        response = client.post(
            "/api/v1/chat/stream",
            json={
                "messages": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi there!"},
                    {"role": "user", "content": "How are you?"},
                ]
            },
        )

        assert response.status_code == 200

    def test_chat_stream_with_session_id(self, client, mock_chat_service):
        """Test that chat stream accepts session_id parameter in body."""
        response = client.post(
            "/api/v1/chat/stream",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "session_id": "test-session-123",
            },
        )

        assert response.status_code == 200

    def test_chat_stream_with_x_session_id_header(self, client, mock_chat_service):
        """Test that chat stream accepts X-Session-ID header."""
        response = client.post(
            "/api/v1/chat/stream",
            json={"messages": [{"role": "user", "content": "Hello"}]},
            headers={"X-Session-ID": "header-session-456"},
        )

        assert response.status_code == 200


class TestChatStreamValidation:
    """Tests for chat stream request validation."""

    def test_chat_stream_requires_messages(self, client):
        """Test that chat stream requires messages field."""
        response = client.post("/api/v1/chat/stream", json={})

        assert response.status_code == 422

    def test_chat_stream_requires_non_empty_messages(self, client):
        """Test that chat stream requires at least one message."""
        response = client.post("/api/v1/chat/stream", json={"messages": []})

        assert response.status_code == 422

    def test_chat_stream_validates_message_role(self, client):
        """Test that chat stream validates message role."""
        response = client.post(
            "/api/v1/chat/stream",
            json={"messages": [{"role": "invalid", "content": "Hello"}]},
        )

        assert response.status_code == 422

    def test_chat_stream_requires_message_content(self, client):
        """Test that chat stream requires message content."""
        response = client.post(
            "/api/v1/chat/stream",
            json={"messages": [{"role": "user"}]},
        )

        assert response.status_code == 422

"""
Integration tests for the chat streaming endpoint.

Tests:
    - POST /api/v1/chat/stream returns SSE stream
    - Response format is compatible with Vercel AI SDK
    - Error handling for invalid requests
"""


class TestChatStream:
    """Tests for the chat streaming endpoint."""

    def test_chat_stream_returns_200(self, client):
        """Test that chat stream endpoint returns 200 OK."""
        response = client.post(
            "/api/v1/chat/stream",
            json={"messages": [{"role": "user", "content": "Hello"}]},
        )

        assert response.status_code == 200

    def test_chat_stream_returns_sse_content_type(self, client):
        """Test that chat stream returns text/event-stream content type."""
        response = client.post(
            "/api/v1/chat/stream",
            json={"messages": [{"role": "user", "content": "Hello"}]},
        )

        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    def test_chat_stream_has_correct_headers(self, client):
        """Test that chat stream has proper SSE headers."""
        response = client.post(
            "/api/v1/chat/stream",
            json={"messages": [{"role": "user", "content": "Hello"}]},
        )

        assert response.headers["cache-control"] == "no-cache"

    def test_chat_stream_returns_data_chunks(self, client):
        """Test that chat stream returns data: prefixed chunks."""
        response = client.post(
            "/api/v1/chat/stream",
            json={"messages": [{"role": "user", "content": "Hello"}]},
        )

        content = response.text
        # Should contain data: prefixed lines
        assert "data:" in content

    def test_chat_stream_ends_with_done(self, client):
        """Test that chat stream ends with [DONE] signal."""
        response = client.post(
            "/api/v1/chat/stream",
            json={"messages": [{"role": "user", "content": "Hello"}]},
        )

        content = response.text
        assert "data: [DONE]" in content

    def test_chat_stream_echoes_user_message(self, client):
        """Test that placeholder echoes back user message."""
        response = client.post(
            "/api/v1/chat/stream",
            json={"messages": [{"role": "user", "content": "test message"}]},
        )

        content = response.text
        # Placeholder should echo back the user message
        assert "test" in content or "message" in content

    def test_chat_stream_with_system_message(self, client):
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

    def test_chat_stream_with_conversation_history(self, client):
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

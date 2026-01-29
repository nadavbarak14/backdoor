"""
Unit tests for the ChatService.

Tests:
    - Message conversion to LangChain format
    - Session management (create, update, clear)
    - System prompt initialization
"""

from unittest.mock import patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.schemas.chat import ChatMessage
from src.services.chat_service import (
    SYSTEM_PROMPT,
    ChatService,
    _session_store,
    get_session_history,
)


class TestChatServiceMessageConversion:
    """Tests for message conversion to LangChain format."""

    @pytest.fixture
    def chat_service(self):
        """Create a ChatService with mocked LLM."""
        with patch("src.services.chat_service.ChatOpenAI"):
            service = ChatService()
            return service

    def test_converts_user_message_to_human_message(self, chat_service):
        """Test that user messages are converted to HumanMessage."""
        messages = [ChatMessage(role="user", content="Hello")]

        result = chat_service._to_langchain_messages(messages)

        assert len(result) == 1
        assert isinstance(result[0], HumanMessage)
        assert result[0].content == "Hello"

    def test_converts_assistant_message_to_ai_message(self, chat_service):
        """Test that assistant messages are converted to AIMessage."""
        messages = [ChatMessage(role="assistant", content="Hi there")]

        result = chat_service._to_langchain_messages(messages)

        assert len(result) == 1
        assert isinstance(result[0], AIMessage)
        assert result[0].content == "Hi there"

    def test_converts_system_message_to_system_message(self, chat_service):
        """Test that system messages are converted to SystemMessage."""
        messages = [ChatMessage(role="system", content="You are helpful")]

        result = chat_service._to_langchain_messages(messages)

        assert len(result) == 1
        assert isinstance(result[0], SystemMessage)
        assert result[0].content == "You are helpful"

    def test_converts_mixed_messages(self, chat_service):
        """Test conversion of mixed message types."""
        messages = [
            ChatMessage(role="system", content="Be helpful"),
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="assistant", content="Hi"),
            ChatMessage(role="user", content="How are you?"),
        ]

        result = chat_service._to_langchain_messages(messages)

        assert len(result) == 4
        assert isinstance(result[0], SystemMessage)
        assert isinstance(result[1], HumanMessage)
        assert isinstance(result[2], AIMessage)
        assert isinstance(result[3], HumanMessage)

    def test_converts_empty_list(self, chat_service):
        """Test conversion of empty message list."""
        result = chat_service._to_langchain_messages([])

        assert result == []


class TestChatServiceSessionManagement:
    """Tests for session management functionality."""

    @pytest.fixture(autouse=True)
    def clear_session_store(self):
        """Clear the global session store before each test."""
        _session_store.clear()
        yield
        _session_store.clear()

    @pytest.fixture
    def chat_service(self):
        """Create a ChatService with mocked LLM."""
        with patch("src.services.chat_service.ChatOpenAI"):
            service = ChatService()
            return service

    def test_get_session_messages_creates_new_session(self, chat_service):
        """Test that new sessions are created empty."""
        messages = chat_service._get_session_messages("new-session")

        # New sessions start empty (system prompt is in agent, not session)
        assert len(messages) == 0

    def test_get_session_messages_returns_existing_session(self, chat_service):
        """Test that existing sessions are returned."""
        # Create session
        chat_service._get_session_messages("existing-session")
        # Add a message via the history object
        history = get_session_history("existing-session")
        history.add_message(HumanMessage(content="Test"))

        messages = chat_service._get_session_messages("existing-session")

        assert len(messages) == 1
        assert isinstance(messages[0], HumanMessage)

    def test_update_session_adds_user_and_assistant_messages(self, chat_service):
        """Test that session is updated with user and assistant messages."""
        chat_service._get_session_messages("session-123")

        chat_service._update_session("session-123", "Hello", "Hi there!")

        history = get_session_history("session-123")
        session = list(history.messages)
        assert len(session) == 2  # User + Assistant
        assert isinstance(session[0], HumanMessage)
        assert session[0].content == "Hello"
        assert isinstance(session[1], AIMessage)
        assert session[1].content == "Hi there!"

    def test_clear_session_removes_existing_session(self, chat_service):
        """Test that clear_session removes an existing session."""
        chat_service._get_session_messages("session-to-clear")

        result = chat_service.clear_session("session-to-clear")

        assert result is True
        assert "session-to-clear" not in _session_store

    def test_clear_session_returns_false_for_nonexistent(self, chat_service):
        """Test that clear_session returns False for nonexistent session."""
        result = chat_service.clear_session("nonexistent")

        assert result is False

    def test_get_session_message_count_returns_count(self, chat_service):
        """Test that message count is correctly returned."""
        chat_service._get_session_messages("session-123")
        history = get_session_history("session-123")
        history.add_message(HumanMessage(content="Test"))

        count = chat_service.get_session_message_count("session-123")

        assert count == 1  # Just the user message

    def test_get_session_message_count_returns_zero_for_nonexistent(self, chat_service):
        """Test that zero is returned for nonexistent session."""
        count = chat_service.get_session_message_count("nonexistent")

        assert count == 0


class TestChatServiceSystemPrompt:
    """Tests for system prompt configuration."""

    def test_system_prompt_contains_basketball_context(self):
        """Test that system prompt has basketball analytics context."""
        assert "basketball" in SYSTEM_PROMPT.lower()
        assert "statistics" in SYSTEM_PROMPT.lower() or "stats" in SYSTEM_PROMPT.lower()

    def test_system_prompt_contains_tool_instructions(self):
        """Test that system prompt has tool usage instructions."""
        assert "tool" in SYSTEM_PROMPT.lower()

    def test_system_prompt_contains_reasoning_instructions(self):
        """Test that system prompt has reasoning/thinking instructions."""
        assert "think" in SYSTEM_PROMPT.lower() or "reason" in SYSTEM_PROMPT.lower()


class TestChatServiceBuildMessages:
    """Tests for message building with history."""

    @pytest.fixture(autouse=True)
    def clear_session_store(self):
        """Clear the global session store before each test."""
        _session_store.clear()
        yield
        _session_store.clear()

    @pytest.fixture
    def chat_service(self):
        """Create a ChatService with mocked LLM."""
        with patch("src.services.chat_service.ChatOpenAI"):
            service = ChatService()
            return service

    def test_build_messages_with_empty_history(self, chat_service):
        """Test building messages when history is empty."""
        messages = chat_service._build_messages_with_history("new-session", "Hello")

        assert len(messages) == 1
        assert isinstance(messages[0], HumanMessage)
        assert messages[0].content == "Hello"

    def test_build_messages_includes_history(self, chat_service):
        """Test that history is included in messages."""
        # Add some history
        history = get_session_history("session-123")
        history.add_message(HumanMessage(content="Previous question"))
        history.add_message(AIMessage(content="Previous answer"))

        messages = chat_service._build_messages_with_history(
            "session-123", "New question"
        )

        assert len(messages) == 3
        assert messages[0].content == "Previous question"
        assert messages[1].content == "Previous answer"
        assert messages[2].content == "New question"

    def test_build_messages_limits_history_to_six_messages(self, chat_service):
        """Test that only last 6 messages from history are included."""
        # Add 10 messages to history
        history = get_session_history("session-123")
        for i in range(10):
            history.add_message(HumanMessage(content=f"Message {i}"))

        messages = chat_service._build_messages_with_history("session-123", "New")

        # Should have 6 from history + 1 new = 7
        assert len(messages) == 7
        # First message should be Message 4 (last 6 of 0-9)
        assert messages[0].content == "Message 4"

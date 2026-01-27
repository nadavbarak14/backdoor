"""
Unit tests for the ChatService.

Tests:
    - Message conversion to LangChain format
    - Session management (create, update, clear)
    - System prompt initialization
"""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.schemas.chat import ChatMessage
from src.services.chat_service import (
    BASKETBALL_SYSTEM_PROMPT,
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
        """Test that new sessions are created with system prompt."""
        messages = chat_service._get_session_messages("new-session")

        assert len(messages) == 1
        assert isinstance(messages[0], SystemMessage)
        assert messages[0].content == BASKETBALL_SYSTEM_PROMPT

    def test_get_session_messages_returns_existing_session(self, chat_service):
        """Test that existing sessions are returned."""
        # Create session
        chat_service._get_session_messages("existing-session")
        # Add a message via the history object
        history = get_session_history("existing-session")
        history.add_message(HumanMessage(content="Test"))

        messages = chat_service._get_session_messages("existing-session")

        assert len(messages) == 2
        assert isinstance(messages[1], HumanMessage)

    def test_update_session_adds_user_and_assistant_messages(self, chat_service):
        """Test that session is updated with user and assistant messages."""
        chat_service._get_session_messages("session-123")
        user_messages = [HumanMessage(content="Hello")]

        chat_service._update_session("session-123", user_messages, "Hi there!")

        history = get_session_history("session-123")
        session = list(history.messages)
        assert len(session) == 3  # System + User + Assistant
        assert isinstance(session[1], HumanMessage)
        assert session[1].content == "Hello"
        assert isinstance(session[2], AIMessage)
        assert session[2].content == "Hi there!"

    def test_update_session_ignores_system_messages_from_user(self, chat_service):
        """Test that system messages in user request are not added to history."""
        chat_service._get_session_messages("session-123")
        user_messages = [
            SystemMessage(content="Override system"),
            HumanMessage(content="Hello"),
        ]

        chat_service._update_session("session-123", user_messages, "Hi!")

        history = get_session_history("session-123")
        session = list(history.messages)
        # Should have: original system + user + assistant (not the user's system msg)
        assert len(session) == 3
        assert session[0].content == BASKETBALL_SYSTEM_PROMPT  # Original system
        assert isinstance(session[1], HumanMessage)
        assert isinstance(session[2], AIMessage)

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

        assert count == 2  # System + User

    def test_get_session_message_count_returns_zero_for_nonexistent(self, chat_service):
        """Test that zero is returned for nonexistent session."""
        count = chat_service.get_session_message_count("nonexistent")

        assert count == 0


class TestChatServiceStreaming:
    """Tests for the streaming functionality."""

    @pytest.fixture(autouse=True)
    def clear_session_store(self):
        """Clear the global session store before each test."""
        _session_store.clear()
        yield
        _session_store.clear()

    @pytest.fixture
    def chat_service(self):
        """Create a ChatService with mocked LLM and tools."""
        with (
            patch("src.services.chat_service.ChatOpenAI") as mock_llm_class,
            patch("src.services.chat_service.SessionLocal") as mock_session,
            patch("src.services.chat_service.ALL_TOOLS", []),
        ):  # Empty tools for testing
            mock_llm = MagicMock()
            mock_llm_class.return_value = mock_llm
            mock_session.return_value = MagicMock()
            service = ChatService()
            service.llm = mock_llm
            return service

    @pytest.mark.asyncio
    async def test_stream_yields_content_chunks(self, chat_service):
        """Test that stream yields content from LLM."""
        from langchain_core.messages import AIMessageChunk

        # Mock the bind_tools().astream() chain with real AIMessageChunks
        async def mock_astream(messages):
            for content in ["Hello", " ", "World"]:
                yield AIMessageChunk(content=content)

        mock_llm_with_tools = MagicMock()
        mock_llm_with_tools.astream = mock_astream
        chat_service.llm.bind_tools = MagicMock(return_value=mock_llm_with_tools)

        messages = [ChatMessage(role="user", content="Hi")]
        chunks = []
        async for chunk in chat_service.stream(messages, "test-session"):
            chunks.append(chunk)

        assert chunks == ["Hello", " ", "World"]

    @pytest.mark.asyncio
    async def test_stream_handles_empty_content(self, chat_service):
        """Test that stream handles chunks with empty content."""
        from langchain_core.messages import AIMessageChunk

        async def mock_astream(messages):
            contents = ["Hello", "", "World"]  # Empty content filtered out
            for content in contents:
                yield AIMessageChunk(content=content)

        mock_llm_with_tools = MagicMock()
        mock_llm_with_tools.astream = mock_astream
        chat_service.llm.bind_tools = MagicMock(return_value=mock_llm_with_tools)

        messages = [ChatMessage(role="user", content="Hi")]
        chunks = []
        async for chunk in chat_service.stream(messages, "test-session"):
            chunks.append(chunk)

        assert chunks == ["Hello", "World"]

    @pytest.mark.asyncio
    async def test_stream_updates_session_after_completion(self, chat_service):
        """Test that session is updated after streaming completes."""
        from langchain_core.messages import AIMessageChunk

        async def mock_astream(messages):
            for content in ["Hello ", "World"]:
                yield AIMessageChunk(content=content)

        mock_llm_with_tools = MagicMock()
        mock_llm_with_tools.astream = mock_astream
        chat_service.llm.bind_tools = MagicMock(return_value=mock_llm_with_tools)

        messages = [ChatMessage(role="user", content="Hi")]
        async for _ in chat_service.stream(messages, "test-session"):
            pass

        history = get_session_history("test-session")
        session = list(history.messages)
        # Session should have: system + user + assistant
        assert len(session) == 3
        assert isinstance(session[-1], AIMessage)
        assert session[-1].content == "Hello World"

    @pytest.mark.asyncio
    async def test_stream_handles_llm_error(self, chat_service):
        """Test that stream handles LLM errors gracefully."""

        async def mock_astream(messages):
            raise Exception("LLM Error")
            yield  # Make it an async generator

        mock_llm_with_tools = MagicMock()
        mock_llm_with_tools.astream = mock_astream
        chat_service.llm.bind_tools = MagicMock(return_value=mock_llm_with_tools)

        messages = [ChatMessage(role="user", content="Hi")]
        chunks = []
        async for chunk in chat_service.stream(messages, "test-session"):
            chunks.append(chunk)

        # Should yield an error message
        assert len(chunks) == 1
        assert "error" in chunks[0].lower()

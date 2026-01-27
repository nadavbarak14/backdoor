"""
Chat Service Module

Provides AI-powered chat functionality using LangChain with GPT-5 nano.
Handles conversation orchestration, streaming responses, and tool binding
for basketball analytics queries.

This service integrates with the LangChain ChatOpenAI model and provides:
- Streaming responses compatible with Vercel AI SDK
- Session-based conversation history (in-memory)
- Tool binding for database queries (future: Ticket 5)
- Basketball analytics context via system prompt

Usage:
    from src.services.chat_service import ChatService
    from src.schemas.chat import ChatMessage

    chat_service = ChatService()

    messages = [ChatMessage(role="user", content="What are LeBron's stats?")]
    async for chunk in chat_service.stream(messages, session_id="abc123"):
        print(chunk)
"""

from collections.abc import AsyncGenerator
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.core.config import settings
from src.schemas.chat import ChatMessage

# System prompt that establishes the basketball analytics assistant context
BASKETBALL_SYSTEM_PROMPT = """You are an expert basketball analytics assistant with deep knowledge of player statistics, team performance, and game analysis.

Your capabilities include:
- Answering questions about player statistics (points, rebounds, assists, etc.)
- Analyzing team performance and trends
- Comparing players and teams
- Providing insights on clutch performance and game situations
- Understanding basketball terminology and advanced metrics

Guidelines:
- For simple lookups (e.g., "What are LeBron's stats?"), provide direct answers
- For complex analytical questions (e.g., "Why is our team bad at clutch?"), break down the analysis
- Always support your insights with specific statistics when available
- Remember conversation context - if the user mentions "we" or "our team", refer to the previously discussed team
- Be concise but thorough in your analysis
- If you don't have specific data, acknowledge it and provide general basketball knowledge instead

You have access to tools that can query the basketball database for real statistics. Use them when specific data is needed."""


class ChatService:
    """
    AI chat service using LangChain with GPT-5 nano.

    Manages chat conversations with streaming support, session-based history,
    and tool binding for basketball analytics queries.

    Attributes:
        llm: The LangChain ChatOpenAI instance configured for streaming.
        sessions: In-memory storage for conversation history by session ID.
        tools: List of tools available for the LLM to use (populated in Ticket 5).

    Example:
        >>> service = ChatService()
        >>> messages = [ChatMessage(role="user", content="Who leads in scoring?")]
        >>> async for chunk in service.stream(messages, "session-123"):
        ...     print(chunk, end="")
        The current scoring leader is...
    """

    def __init__(self) -> None:
        """
        Initialize the chat service with LangChain ChatOpenAI.

        Configures the LLM with settings from environment variables
        and initializes empty session storage.

        Raises:
            ValueError: If LLM_API_KEY is not configured.
        """
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.LLM_API_KEY or None,
            base_url=settings.LLM_BASE_URL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            streaming=True,
        )
        self.sessions: dict[str, list[BaseMessage]] = {}
        self.tools: list[Any] = []  # Will be populated in Ticket 5

    def _to_langchain_messages(
        self, messages: list[ChatMessage]
    ) -> list[BaseMessage]:
        """
        Convert ChatMessage objects to LangChain message format.

        Maps the role field to the appropriate LangChain message class:
        - "system" -> SystemMessage
        - "user" -> HumanMessage
        - "assistant" -> AIMessage

        Args:
            messages: List of ChatMessage objects from the API request.

        Returns:
            List of LangChain BaseMessage subclass instances.

        Example:
            >>> msgs = [ChatMessage(role="user", content="Hello")]
            >>> lc_msgs = service._to_langchain_messages(msgs)
            >>> isinstance(lc_msgs[0], HumanMessage)
            True
        """
        lc_messages: list[BaseMessage] = []
        for msg in messages:
            if msg.role == "system":
                lc_messages.append(SystemMessage(content=msg.content))
            elif msg.role == "user":
                lc_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                lc_messages.append(AIMessage(content=msg.content))
        return lc_messages

    def _get_session_messages(self, session_id: str) -> list[BaseMessage]:
        """
        Retrieve conversation history for a session.

        If the session doesn't exist, creates a new session with the
        basketball analytics system prompt.

        Args:
            session_id: Unique identifier for the chat session.

        Returns:
            List of LangChain messages representing the conversation history.

        Example:
            >>> msgs = service._get_session_messages("new-session")
            >>> len(msgs)
            1
            >>> isinstance(msgs[0], SystemMessage)
            True
        """
        if session_id not in self.sessions:
            self.sessions[session_id] = [
                SystemMessage(content=BASKETBALL_SYSTEM_PROMPT)
            ]
        return self.sessions[session_id]

    def _update_session(
        self,
        session_id: str,
        user_messages: list[BaseMessage],
        assistant_response: str,
    ) -> None:
        """
        Update session history with new messages and response.

        Appends user messages (excluding any system messages from the request)
        and the complete assistant response to the session history.

        Args:
            session_id: Unique identifier for the chat session.
            user_messages: LangChain messages from the user's request.
            assistant_response: Complete text of the assistant's response.

        Example:
            >>> service._update_session(
            ...     "session-123",
            ...     [HumanMessage(content="Hello")],
            ...     "Hi there!"
            ... )
        """
        # Add non-system user messages to history
        for msg in user_messages:
            if not isinstance(msg, SystemMessage):
                self.sessions[session_id].append(msg)

        # Add assistant response
        self.sessions[session_id].append(AIMessage(content=assistant_response))

    async def stream(
        self,
        messages: list[ChatMessage],
        session_id: str,
    ) -> AsyncGenerator[str, None]:
        """
        Stream a chat response for the given messages.

        Combines session history with new messages, streams the LLM response,
        and updates the session history upon completion.

        Args:
            messages: List of ChatMessage objects from the current request.
            session_id: Unique identifier for the chat session.

        Yields:
            String chunks of the assistant's response as they are generated.

        Raises:
            Exception: If the LLM fails to generate a response. Errors are
                logged and a user-friendly error message is yielded.

        Example:
            >>> messages = [ChatMessage(role="user", content="Hello")]
            >>> async for chunk in service.stream(messages, "session-123"):
            ...     print(chunk, end="")
            Hello! How can I help you with basketball analytics today?
        """
        # Convert incoming messages to LangChain format
        lc_messages = self._to_langchain_messages(messages)

        # Get session history and combine with new messages
        session_history = self._get_session_messages(session_id)

        # Build full message list: session history + new user messages (skip system if in request)
        full_messages = list(session_history)
        for msg in lc_messages:
            if not isinstance(msg, SystemMessage):
                full_messages.append(msg)

        # Bind tools if available (Ticket 5 will populate self.tools)
        llm = self.llm
        if self.tools:
            llm = self.llm.bind_tools(self.tools)

        # Stream the response
        full_response = ""
        try:
            async for chunk in llm.astream(full_messages):
                if chunk.content:
                    content = str(chunk.content)
                    full_response += content
                    yield content
        except Exception as e:
            # Log the error (in production, use proper logging)
            error_msg = f"I apologize, but I encountered an error: {e!s}"
            yield error_msg
            full_response = error_msg

        # Update session with the complete exchange
        self._update_session(session_id, lc_messages, full_response)

    def clear_session(self, session_id: str) -> bool:
        """
        Clear conversation history for a session.

        Removes all messages from the specified session. The next
        interaction will start fresh with only the system prompt.

        Args:
            session_id: Unique identifier for the chat session to clear.

        Returns:
            True if the session existed and was cleared, False otherwise.

        Example:
            >>> service.clear_session("session-123")
            True
            >>> service.clear_session("nonexistent")
            False
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def get_session_message_count(self, session_id: str) -> int:
        """
        Get the number of messages in a session's history.

        Args:
            session_id: Unique identifier for the chat session.

        Returns:
            Number of messages in the session, or 0 if session doesn't exist.

        Example:
            >>> service.get_session_message_count("session-123")
            5
        """
        return len(self.sessions.get(session_id, []))

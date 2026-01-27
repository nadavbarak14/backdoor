"""
Chat Service Module

Provides AI-powered chat functionality using LangChain with tool execution.
Handles conversation orchestration, streaming responses, and tool binding
for basketball analytics queries.

This service integrates with the LangChain ChatOpenAI model and provides:
- Streaming responses compatible with Vercel AI SDK
- Session-based conversation history using LangChain's InMemoryChatMessageHistory
- Tool binding for database queries with automatic execution
- Basketball analytics context via system prompt

Usage:
    from src.services.chat_service import ChatService
    from src.schemas.chat import ChatMessage

    chat_service = ChatService()

    messages = [ChatMessage(role="user", content="What are LeBron's stats?")]
    async for chunk in chat_service.stream(messages, session_id="abc123"):
        print(chunk)
"""

import inspect
import logging
from collections.abc import AsyncGenerator
from functools import wraps
from typing import Any

from langchain_core.chat_history import InMemoryChatMessageHistory

logger = logging.getLogger(__name__)
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.database import SessionLocal
from src.schemas.chat import ChatMessage
from src.services.chat_tools import ALL_TOOLS

# System prompt that establishes the basketball analytics assistant context
BASKETBALL_SYSTEM_PROMPT = """You are an expert basketball analytics assistant with deep knowledge of player statistics, team performance, and game analysis.

Your capabilities include:
- Answering questions about player statistics (points, rebounds, assists, etc.)
- Analyzing team performance and trends
- Comparing players and teams
- Providing insights on clutch performance and game situations
- Understanding basketball terminology and advanced metrics

You have access to tools that can query the basketball database for real statistics.

IMPORTANT INSTRUCTIONS:
1. When a user asks about stats, players, teams, or games, you MUST use the appropriate tool to get real data.
2. DO NOT make up statistics or say what you "would" do - actually call the tools.
3. If a tool returns data, present it clearly to the user.
4. If a tool returns an error or no data, tell the user what happened.
5. For simple greetings or non-basketball questions, respond conversationally without tools.

Available tools:
- search_players: Find players by name
- search_teams: Find teams by name
- get_team_roster: Get a team's player roster
- get_player_stats: Get a player's season statistics
- get_player_games: Get a player's recent game log
- get_league_leaders: Get top players in a statistical category
- get_game_details: Get box score for a specific game
- get_clutch_stats: Analyze clutch performance
- get_quarter_splits: Performance by quarter
- get_trend: Analyze recent performance trends
- get_lineup_stats: Stats for specific player combinations
- get_home_away_split: Home vs away performance
- get_on_off_stats: Team performance with player on/off court
- get_vs_opponent: Stats against specific opponent

Remember: Always use tools for data queries. Never fabricate statistics."""

# Global session store using LangChain's InMemoryChatMessageHistory
_session_store: dict[str, InMemoryChatMessageHistory] = {}


def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    """
    Get or create chat history for a session.

    Uses LangChain's InMemoryChatMessageHistory for per-session message storage.
    New sessions are initialized with the basketball analytics system prompt.

    Args:
        session_id: Unique identifier for the chat session.

    Returns:
        InMemoryChatMessageHistory instance for the session.

    Example:
        >>> history = get_session_history("session-123")
        >>> len(history.messages)
        1  # System prompt
    """
    if session_id not in _session_store:
        history = InMemoryChatMessageHistory()
        history.add_message(SystemMessage(content=BASKETBALL_SYSTEM_PROMPT))
        _session_store[session_id] = history
    return _session_store[session_id]


def _create_tool_with_db(tool_func: Any, db: Session) -> StructuredTool:
    """
    Create a LangChain tool with database session injected.

    Wraps the original tool function to automatically inject the db parameter,
    so the LLM only needs to provide the user-facing parameters.

    Args:
        tool_func: The original @tool decorated function.
        db: Database session to inject.

    Returns:
        StructuredTool with db pre-bound.
    """
    # Get the original function's signature
    original_func = tool_func.func if hasattr(tool_func, "func") else tool_func
    sig = inspect.signature(original_func)

    # Create new parameters without 'db'
    new_params = [p for name, p in sig.parameters.items() if name != "db"]

    @wraps(original_func)
    def wrapper(**kwargs: Any) -> str:
        # Inject db into the call
        kwargs["db"] = db
        return original_func(**kwargs)

    # Update wrapper signature to exclude db
    wrapper.__signature__ = sig.replace(parameters=new_params)  # type: ignore

    # Get tool metadata
    name = tool_func.name if hasattr(tool_func, "name") else original_func.__name__
    description = (
        tool_func.description
        if hasattr(tool_func, "description")
        else (original_func.__doc__ or "")
    )

    # Create StructuredTool from the wrapper
    return StructuredTool.from_function(
        func=wrapper,
        name=name,
        description=description,
    )


class ChatService:
    """
    AI chat service using LangChain with tool execution.

    Manages chat conversations with streaming support, session-based history
    via LangChain's InMemoryChatMessageHistory, and tool binding for
    basketball analytics queries.

    Attributes:
        llm: The LangChain ChatOpenAI instance configured for streaming.

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

        Configures the LLM with settings from environment variables.
        Session storage uses the global _session_store via get_session_history.

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

    def _to_langchain_messages(self, messages: list[ChatMessage]) -> list[BaseMessage]:
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

        Uses the global session store via get_session_history.
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
        history = get_session_history(session_id)
        return list(history.messages)

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
        history = get_session_history(session_id)

        # Add non-system user messages to history
        for msg in user_messages:
            if not isinstance(msg, SystemMessage):
                history.add_message(msg)

        # Add assistant response
        history.add_message(AIMessage(content=assistant_response))

    def _create_tools_with_session(self, db: Session) -> list[StructuredTool]:
        """
        Create tool instances with database session injected.

        Args:
            db: Database session to inject into all tools.

        Returns:
            List of StructuredTool instances ready for LLM binding.
        """
        return [_create_tool_with_db(tool, db) for tool in ALL_TOOLS]

    def _execute_tool(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        tools: list[StructuredTool],
    ) -> str:
        """
        Execute a tool by name with given arguments.

        Args:
            tool_name: Name of the tool to execute.
            tool_args: Arguments to pass to the tool.
            tools: List of available tools.

        Returns:
            Tool execution result as string.
        """
        for tool in tools:
            if tool.name == tool_name:
                try:
                    result = tool.invoke(tool_args)
                    return str(result)
                except Exception as e:
                    return f"Error executing {tool_name}: {e!s}"
        return f"Tool '{tool_name}' not found."

    async def stream(
        self,
        messages: list[ChatMessage],
        session_id: str,
    ) -> AsyncGenerator[str, None]:
        """
        Stream a chat response for the given messages.

        Combines session history with new messages, streams the LLM response,
        handles tool calls, and updates the session history upon completion.

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
        # Create database session for this request
        db = SessionLocal()

        try:
            # Create tools with db session injected
            tools = self._create_tools_with_session(db)

            # Bind tools to LLM
            llm_with_tools = self.llm.bind_tools(tools)

            # Convert incoming messages to LangChain format
            lc_messages = self._to_langchain_messages(messages)

            # Get session history and combine with new messages
            session_history = self._get_session_messages(session_id)

            # Build full message list: session history + new user messages
            full_messages: list[BaseMessage] = list(session_history)
            for msg in lc_messages:
                if not isinstance(msg, SystemMessage):
                    full_messages.append(msg)

            # Stream the response with potential tool calls
            full_response = ""
            max_tool_iterations = 5  # Prevent infinite loops

            for iteration in range(max_tool_iterations):
                try:
                    # Log context size before LLM call
                    total_chars = sum(
                        len(m.content) if isinstance(m.content, str) else 0
                        for m in full_messages
                    )
                    token_estimate = total_chars // 4
                    logger.info(
                        f"[LLM_CONTEXT] session={session_id} iteration={iteration} "
                        f"messages={len(full_messages)} chars={total_chars} "
                        f"~tokens={token_estimate}"
                    )

                    # Stream response and collect chunks for tool call aggregation
                    collected_chunks: list[Any] = []

                    async for chunk in llm_with_tools.astream(full_messages):
                        collected_chunks.append(chunk)

                        # Stream text content immediately as it arrives
                        if chunk.content:
                            content = str(chunk.content)
                            full_response += content
                            yield content

                    # After streaming completes, aggregate chunks to check for tool calls
                    # Merge all chunks into a single message
                    if not collected_chunks:
                        break

                    # Aggregate chunks into final message
                    final_message = collected_chunks[0]
                    for chunk in collected_chunks[1:]:
                        final_message = final_message + chunk

                    # Check for tool calls in the aggregated message
                    if (
                        not hasattr(final_message, "tool_calls")
                        or not final_message.tool_calls
                    ):
                        break

                    # Add AI message with tool calls to history
                    full_messages.append(final_message)

                    # Show user that we're fetching data (immediate feedback)
                    yield "🔍 "

                    # Execute each tool and add results
                    for tool_call in final_message.tool_calls:
                        tool_name = tool_call["name"]
                        tool_args = tool_call["args"]
                        # Ensure tool_id is never None
                        tool_id = tool_call.get("id") or f"call_{tool_name}_{iteration}"

                        # Execute the tool
                        result = self._execute_tool(tool_name, tool_args, tools)

                        # Log tool result size
                        result_chars = len(result)
                        result_tokens = result_chars // 4
                        logger.info(
                            f"[TOOL_RESULT] {tool_name}: {result_chars} chars "
                            f"~{result_tokens} tokens args={tool_args}"
                        )

                        # Add tool result to messages
                        tool_message = ToolMessage(
                            content=result,
                            tool_call_id=tool_id,
                        )
                        full_messages.append(tool_message)

                    # Show that data was found and we're preparing response
                    yield "Found data, preparing response...\n\n"

                    # Reset for next iteration (LLM will process tool results)
                    full_response = ""

                except Exception as e:
                    error_msg = f"I apologize, but I encountered an error: {e!s}"
                    yield error_msg
                    full_response = error_msg
                    break

            # Update session with the complete exchange
            self._update_session(session_id, lc_messages, full_response)

        finally:
            # Always close the database session
            db.close()

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
        if session_id in _session_store:
            del _session_store[session_id]
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
        if session_id not in _session_store:
            return 0
        return len(_session_store[session_id].messages)

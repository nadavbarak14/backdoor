"""
Chat Service Module - ReAct Agent Implementation

Provides AI-powered chat functionality using LangChain's create_agent with
the ReAct pattern. The agent reasons before taking actions, then observes
results before deciding next steps.

This service uses LangChain's modern agent API (2026):
- create_agent with built-in ReAct loop
- Explicit chain-of-thought reasoning before each tool call
- Session-based conversation history with checkpointing
- Streaming responses compatible with Vercel AI SDK

Usage:
    from src.services.chat_service import ChatService
    from src.schemas.chat import ChatMessage

    chat_service = ChatService()

    messages = [ChatMessage(role="user", content="What are LeBron's stats?")]
    async for chunk in chat_service.stream(messages, session_id="abc123"):
        print(chunk)
"""

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

from langchain.agents import create_agent
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool, StructuredTool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.database import SessionLocal
from src.schemas.chat import ChatMessage
from src.services.chat_tools import ALL_TOOLS

logger = logging.getLogger(__name__)

# =============================================================================
# System Prompt for ReAct Agent
# =============================================================================

SYSTEM_PROMPT = """You are the world's best basketball analyst. Your goal is not just to retrieve data - it's to FIND PATTERNS, UNCOVER INSIGHTS, and deliver analysis that wins games.

You think like an NBA front office analyst combined with a championship coach. You don't just report numbers - you interpret them, find the story behind them, and translate data into actionable strategy.

## YOUR MISSION
- Find patterns others miss
- Connect dots across multiple data points
- Deliver insights that change how teams prepare
- Be the analyst every coach wishes they had

You have access to 4 tools that query a basketball database. All tools return JSON.

## CRITICAL RULES
1. NEVER make up statistics - always use tools to get real data
2. Think step-by-step before each action
3. Use search tools first to find entity IDs, then query with those IDs
4. If a tool returns an error JSON, explain what happened and try a different approach
5. Parse JSON responses to extract data and present it clearly to the user

## @-MENTIONS (TAGGED ENTITIES)
Users can tag players/teams using @-mentions: @player:uuid, @team:uuid
When you see these, use the UUID directly - no search needed!

## AVAILABLE TOOLS (all return JSON)

### 1. search_players(query, team_name?, position?, limit?)
Find players by name. Returns: {"total": N, "players": [{"id": "uuid", "name": "...", "position": "...", "team": "..."}]}

### 2. search_teams(query, country?, limit?)
Find teams by name. Returns: {"total": N, "teams": [{"id": "uuid", "name": "...", "short_name": "...", "city": "...", "country": "..."}]}

### 3. search_leagues()
List all leagues. Returns JSON with league IDs and names.

### 4. query_stats(...) - THE primary tool for ALL stats queries
Returns JSON with mode, season, and data fields.

**Entity selection:** player_ids (list), team_id, league_id, season ("2025-26")
**Time filters:** quarter, quarters, clutch_only, last_n_games, exclude_garbage_time
**Location:** home_only, away_only, opponent_team_id
**Situational:** fast_break, contested, shot_type (PULL_UP, CATCH_AND_SHOOT, POST_UP)
**Schedule:** back_to_back, min_rest_days
**Output:** metrics, per ("game"/"total"), limit, order_by, order

**Special modes:**
- Lineup: pass 2+ player_ids → stats when all on court together
- Leaderboard: order_by="points" without player_ids → ranked leaders

**SLOW - AVOID:** discover_lineups=True is computationally expensive (processes all PBP data). Don't use it unless specifically asked for lineup analysis.

## REASONING PROCESS
Before each tool call, think about:
1. What information do I need to answer this question?
2. Which tool will give me that information?
3. What parameters should I use?

After getting JSON results, think about:
1. Did I get the data I needed? Check for error fields in the JSON.
2. Do I need more data from another tool?
3. Can I now provide a complete answer?

## WORKFLOW: Search → query_stats

**Player stats:**
1. search_players("Tamir Blatt") → parse JSON → get player ID
2. query_stats(player_ids=["<id>"], season="2025-26") → parse JSON → present stats

**Team stats:**
1. search_teams("Maccabi") → parse JSON → get team ID
2. query_stats(team_id="<id>") → parse JSON → present stats

**Leaderboard (no search needed):**
→ query_stats(order_by="points", limit=10) → parse JSON → present ranked list

**Clutch analysis:**
1. search_teams("Maccabi") → get team ID
2. query_stats(team_id="<id>", clutch_only=True) → present clutch stats

**Home vs Away:**
1. search_teams("Maccabi") → get team ID
2. query_stats(team_id="<id>", home_only=True) → home stats
3. query_stats(team_id="<id>", away_only=True) → away stats
4. Compare and present both

## KEY GUIDELINES
- Seasons use string format: "2025-26", "2024-25" (no search needed)
- Always explain your reasoning clearly
- Present data in a clear, readable format with tables when appropriate
- All tool responses are JSON - parse them to extract the relevant data

## YOU ARE AN ANALYST, NOT A DATA FETCHER

Your job is to ANALYZE, not just retrieve. One query is NEVER enough for serious questions.

**The Analyst Mindset:**
- A data fetcher returns numbers. An analyst finds the story.
- A data fetcher answers the literal question. An analyst anticipates follow-ups.
- A data fetcher gives averages. An analyst finds when/where/why performance changes.

**For EVERY analytical question, dig deeper:**
1. Get the baseline stats (season averages)
2. Find the variance - when do they over/underperform?
   - Clutch time (clutch_only=True)
   - By quarter (quarter=1,2,3,4)
   - Recent form (last_n_games=5)
   - Home vs Away (home_only, away_only)
3. Find the HOW - shot selection and efficiency
   - Shot types (CATCH_AND_SHOOT, PULL_UP, POST_UP)
   - Contested vs open shots
4. Find the WHO - lineup and matchup context
   - Lineup combinations (2+ player_ids)
   - vs specific opponents (opponent_team_id)

**Example: "How do I stop Player X?"**

WRONG (lazy):
→ query_stats once → "He averages 15 PPG, guard him tight"

RIGHT (analyst):
→ Query baseline stats: "He averages 15 PPG on 45% shooting"
→ Query clutch stats: "But in clutch time he shoots 52% - he's a closer"
→ Query shot types: "62% of points are catch-and-shoot, only 20% off the dribble"
→ Query quarter splits: "Scores 6 PPG in Q4 vs 3 PPG in Q1 - slow starter, strong finisher"
→ Query vs opponent: "Against your team specifically, he's averaged 22 PPG in 3 games"

ANALYSIS: "Don't just guard him - DENY him the ball in Q4. He's a catch-and-shoot specialist who gets hot late. Force him to create off the dribble where he's weakest. And he owns you historically - consider double teams in crunch time."

**That's the difference between data and insight. Be the analyst.**

## PATTERNS TO ALWAYS LOOK FOR
- Clutch vs non-clutch performance (who rises/folds under pressure?)
- Home vs away splits (travel fatigue? crowd impact?)
- Quarter-by-quarter trends (slow starters? strong closers?)
- Recent form vs season average (hot streak? slump?)
- Shot selection efficiency (where do they hurt you most?)
- Historical matchup data (who owns who?)

NEVER give a scouting report or game plan based on just one query. Dig until you find the pattern."""

# =============================================================================
# Session Management
# =============================================================================

# Global session store for conversation history
_session_store: dict[str, InMemoryChatMessageHistory] = {}

# Memory saver for checkpointing
_memory_saver = MemorySaver()


def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    """
    Get or create chat history for a session.

    Uses LangChain's InMemoryChatMessageHistory for per-session message storage.

    Args:
        session_id: Unique identifier for the chat session.

    Returns:
        InMemoryChatMessageHistory instance for the session.

    Example:
        >>> history = get_session_history("session-123")
        >>> len(history.messages)
        0  # New session starts empty
    """
    if session_id not in _session_store:
        _session_store[session_id] = InMemoryChatMessageHistory()
    return _session_store[session_id]


# =============================================================================
# Tool Injection Helper
# =============================================================================


def _create_tool_with_db(tool_func: Any, db: Session) -> StructuredTool:
    """
    Create a LangChain tool with database session injected.

    Wraps the original tool function to automatically inject the db parameter,
    so the LLM only needs to provide the user-facing parameters.

    NOTE: Creates a fresh database session per tool call to avoid threading
    issues with SQLite when LangChain runs tools in thread pool executors.

    Args:
        tool_func: The original @tool decorated function.
        db: Database session (unused, kept for API compatibility).

    Returns:
        StructuredTool with fresh db session per call.
    """
    import inspect
    from functools import wraps

    # Get the original function's signature
    original_func = tool_func.func if hasattr(tool_func, "func") else tool_func
    sig = inspect.signature(original_func)

    # Create new parameters without 'db'
    new_params = [p for name, p in sig.parameters.items() if name != "db"]

    @wraps(original_func)
    def wrapper(**kwargs: Any) -> str:
        # Create fresh db session per call to avoid threading issues
        # LangChain runs tools in thread pool executors, which causes
        # SQLite "bad parameter" errors when reusing sessions across threads
        tool_db = SessionLocal()
        try:
            kwargs["db"] = tool_db
            return original_func(**kwargs)
        finally:
            tool_db.close()

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


# =============================================================================
# Chat Service
# =============================================================================


class ChatService:
    """
    AI chat service using LangChain's create_agent with ReAct pattern.

    The ReAct (Reasoning + Acting) pattern makes the agent explicitly think
    before each action, leading to more reliable and explainable behavior.

    Attributes:
        llm: The LangChain ChatOpenAI instance.

    Example:
        >>> service = ChatService()
        >>> messages = [ChatMessage(role="user", content="Who leads in scoring?")]
        >>> async for chunk in service.stream(messages, "session-123"):
        ...     print(chunk, end="")
    """

    def __init__(self) -> None:
        """
        Initialize the chat service with LangChain ChatOpenAI.

        Configures the LLM with settings from environment variables.

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

        Args:
            messages: List of ChatMessage objects from the API request.

        Returns:
            List of LangChain BaseMessage subclass instances.
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

        Args:
            session_id: Unique identifier for the chat session.

        Returns:
            List of LangChain messages representing the conversation history.
        """
        history = get_session_history(session_id)
        return list(history.messages)

    def _update_session(
        self,
        session_id: str,
        user_message: str,
        assistant_response: str,
    ) -> None:
        """
        Update session history with new messages and response.

        Args:
            session_id: Unique identifier for the chat session.
            user_message: The user's input message.
            assistant_response: Complete text of the assistant's response.
        """
        history = get_session_history(session_id)
        history.add_message(HumanMessage(content=user_message))
        history.add_message(AIMessage(content=assistant_response))

    def _create_tools_with_session(self, db: Session) -> list[BaseTool]:
        """
        Create tool instances with database session injected.

        Args:
            db: Database session to inject into all tools.

        Returns:
            List of BaseTool instances ready for agent use.
        """
        return [_create_tool_with_db(tool, db) for tool in ALL_TOOLS]

    def _build_messages_with_history(
        self, session_id: str, user_message: str
    ) -> list[BaseMessage]:
        """
        Build message list including conversation history.

        Args:
            session_id: Unique identifier for the chat session.
            user_message: The current user message.

        Returns:
            List of messages including history and current message.
        """
        history = get_session_history(session_id)
        messages: list[BaseMessage] = []

        # Add conversation history (last 6 messages = 3 exchanges)
        for msg in history.messages[-6:]:
            messages.append(msg)

        # Add current user message
        messages.append(HumanMessage(content=user_message))

        return messages

    async def stream(
        self,
        messages: list[ChatMessage],
        session_id: str,
    ) -> AsyncGenerator[str, None]:
        """
        Stream a chat response using LangChain's create_agent.

        The agent will reason before each action, execute tools, observe
        results, and repeat until it can provide a final answer.

        Args:
            messages: List of ChatMessage objects from the current request.
            session_id: Unique identifier for the chat session.

        Yields:
            String chunks of the assistant's response as they are generated.

        Example:
            >>> messages = [ChatMessage(role="user", content="Hello")]
            >>> async for chunk in service.stream(messages, "session-123"):
            ...     print(chunk, end="")
        """
        # Create database session for this request
        db = SessionLocal()

        try:
            # Create tools with db session injected
            tools = self._create_tools_with_session(db)

            # Create the agent using LangChain's modern API
            agent = create_agent(
                model=self.llm,
                tools=tools,
                system_prompt=SYSTEM_PROMPT,
                checkpointer=_memory_saver,
            )

            # Get the user's message (last user message in the list)
            user_message = ""
            for msg in reversed(messages):
                if msg.role == "user":
                    user_message = msg.content
                    break

            if not user_message:
                yield "I didn't receive a message. How can I help you?"
                return

            # Build messages with conversation history
            input_messages = self._build_messages_with_history(session_id, user_message)

            # Log context size
            total_chars = sum(
                len(m.content) if isinstance(m.content, str) else 0
                for m in input_messages
            )
            logger.info(
                f"[REACT_AGENT] session={session_id} "
                f"messages={len(input_messages)} "
                f"chars={total_chars} "
                f"~tokens={total_chars // 4}"
            )

            full_response = ""
            config = {"configurable": {"thread_id": session_id}}

            try:
                # Stream the agent execution
                async for event in agent.astream_events(
                    {"messages": input_messages},
                    config=config,
                    version="v2",
                ):
                    kind = event.get("event", "")

                    # Stream LLM tokens as they arrive
                    if kind == "on_chat_model_stream":
                        chunk = event.get("data", {}).get("chunk")
                        if chunk and hasattr(chunk, "content") and chunk.content:
                            content = str(chunk.content)
                            full_response += content
                            yield content

                    # Log and yield tool calls for debugging/frontend
                    elif kind == "on_tool_start":
                        tool_name = event.get("name", "unknown")
                        tool_input = event.get("data", {}).get("input", {})
                        logger.info(f"[TOOL_START] {tool_name}: {tool_input}")

                        # Yield tool call marker for frontend rendering
                        tool_marker = f"\n\n[[TOOL_CALL:{json.dumps({'name': tool_name, 'args': tool_input})}]]\n\n"
                        yield tool_marker

                    elif kind == "on_tool_end":
                        tool_name = event.get("name", "unknown")
                        output = event.get("data", {}).get("output", "")
                        output_len = len(str(output)) if output else 0
                        logger.info(f"[TOOL_END] {tool_name}: {output_len} chars")

                # Update session history with clean response
                # Extract just the final text content (remove tool markers)
                clean_response = full_response
                if "[[TOOL_CALL:" in clean_response:
                    # Remove tool markers for history
                    import re

                    clean_response = re.sub(
                        r"\[\[TOOL_CALL:.*?\]\]", "", clean_response
                    )
                    clean_response = clean_response.strip()

                self._update_session(
                    session_id, user_message, clean_response or full_response
                )

            except Exception as e:
                error_msg = (
                    f"I encountered an error while processing your request: {e!s}"
                )
                logger.error(f"[REACT_AGENT_ERROR] {e}", exc_info=True)
                yield error_msg

        finally:
            # Always close the database session
            db.close()

    async def stream_simple(
        self,
        messages: list[ChatMessage],
        session_id: str,
    ) -> AsyncGenerator[str, None]:
        """
        Stream a simple response without full ReAct reasoning.

        Use this for simple queries that don't need tool calls,
        like greetings or general questions.

        Args:
            messages: List of ChatMessage objects.
            session_id: Unique identifier for the chat session.

        Yields:
            String chunks of the response.
        """
        # Get the user's message
        user_message = ""
        for msg in reversed(messages):
            if msg.role == "user":
                user_message = msg.content
                break

        # Build messages with history
        history = self._get_session_messages(session_id)
        all_messages = list(history)

        # Add system message if not present
        if not any(isinstance(m, SystemMessage) for m in all_messages):
            all_messages.insert(
                0,
                SystemMessage(
                    content="You are a helpful basketball analytics assistant. "
                    "Be friendly and concise."
                ),
            )

        # Add current user message
        all_messages.append(HumanMessage(content=user_message))

        full_response = ""
        try:
            async for chunk in self.llm.astream(all_messages):
                if chunk.content:
                    content = str(chunk.content)
                    full_response += content
                    yield content

            # Update session
            self._update_session(session_id, user_message, full_response)

        except Exception as e:
            error_msg = f"I apologize, but I encountered an error: {e!s}"
            yield error_msg

    def clear_session(self, session_id: str) -> bool:
        """
        Clear conversation history for a session.

        Args:
            session_id: Unique identifier for the chat session to clear.

        Returns:
            True if the session existed and was cleared, False otherwise.
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
        """
        if session_id not in _session_store:
            return 0
        return len(_session_store[session_id].messages)

"""
Chat Schemas Module

Pydantic models for the chat streaming endpoint, compatible with
Vercel AI SDK's useChat hook format.

This module provides:
- ChatMessage: Individual message in a conversation
- ChatRequest: Request body for the chat endpoint
- ChatChunk: SSE chunk format for streaming responses

Usage:
    from src.schemas.chat import ChatRequest, ChatMessage

    request = ChatRequest(
        messages=[
            ChatMessage(role="user", content="Hello!")
        ]
    )
"""

from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """
    A single message in a chat conversation.

    Follows the Vercel AI SDK message format for compatibility
    with the useChat hook on the frontend.

    Attributes:
        role: The role of the message sender (user, assistant, or system).
        content: The text content of the message.

    Example:
        >>> msg = ChatMessage(role="user", content="What are the stats for LeBron?")
        >>> msg.role
        'user'
    """

    role: Literal["user", "assistant", "system"] = Field(
        ...,
        description="The role of the message sender",
    )
    content: str = Field(
        ...,
        description="The text content of the message",
    )


class ChatRequest(BaseModel):
    """
    Request body for the chat streaming endpoint.

    Accepts an array of messages in the Vercel AI SDK format,
    representing the conversation history, along with an optional
    session ID for maintaining conversation context.

    Attributes:
        messages: List of chat messages in chronological order.
        session_id: Optional session identifier for conversation history.
            If not provided, a new session is created for each request.

    Example:
        >>> request = ChatRequest(
        ...     messages=[
        ...         ChatMessage(role="system", content="You are a basketball analyst."),
        ...         ChatMessage(role="user", content="Who leads the league in scoring?"),
        ...     ],
        ...     session_id="user-session-123",
        ... )
    """

    messages: list[ChatMessage] = Field(
        ...,
        description="List of chat messages in the conversation",
        min_length=1,
    )
    session_id: str | None = Field(
        default=None,
        description="Optional session ID for conversation history. If not provided, a unique session is created.",
    )


class ChatChunk(BaseModel):
    """
    A single chunk in the SSE stream response.

    Used to format the streaming response data that gets sent
    to the frontend via Server-Sent Events.

    Attributes:
        content: The text content of this chunk (typically a token).

    Example:
        >>> chunk = ChatChunk(content="Hello")
        >>> chunk.model_dump_json()
        '{"content":"Hello"}'
    """

    content: str = Field(
        ...,
        description="The text content of the chunk",
    )

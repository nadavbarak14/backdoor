"""
Chat Router Module

FastAPI router for the AI-powered chat streaming endpoint.
Provides a Server-Sent Events (SSE) endpoint compatible with
Vercel AI SDK's useChat hook.

Endpoints:
    POST /chat/stream - Stream chat responses via SSE

Usage:
    from src.api.v1.chat import router

    app.include_router(router, prefix="/api/v1")
"""

import json
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Header, status
from fastapi.responses import StreamingResponse

from src.schemas.chat import ChatRequest
from src.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["Chat"])

# Module-level chat service instance (singleton pattern)
# In production, consider using FastAPI dependency injection for better testability
_chat_service: ChatService | None = None


def get_chat_service() -> ChatService:
    """
    Get or create the chat service singleton.

    Returns:
        ChatService: The shared chat service instance.

    Example:
        >>> service = get_chat_service()
        >>> isinstance(service, ChatService)
        True
    """
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service


async def _generate_stream(
    request: ChatRequest,
    session_id: str,
) -> AsyncGenerator[str, None]:
    """
    Generate streaming response from the LLM.

    Wraps the ChatService stream method to format output compatible with
    Vercel AI SDK's Data Stream Protocol v1.

    Format:
        - Text chunks: 0:"text content"\\n
        - Finish: e:{"finishReason":"stop",...}\\n
        - Done: d:{"finishReason":"stop",...}\\n

    Args:
        request: The chat request containing conversation messages.
        session_id: Unique session identifier from X-Session-ID header or request body.

    Yields:
        Stream chunks in Vercel AI SDK Data Stream Protocol format.

    Example:
        >>> async for chunk in _generate_stream(request, "session-123"):
        ...     print(chunk)
        0:"Hello"
        0:" world"
        ...
    """
    chat_service = get_chat_service()

    # Stream response from LLM as text chunks (0: prefix)
    async for content in chat_service.stream(request.messages, session_id):
        # Format: 0:"text"\n where text is JSON-encoded
        yield f"0:{json.dumps(content)}\n"

    # Send finish event
    finish_event = json.dumps({
        "finishReason": "stop",
        "usage": {"promptTokens": 0, "completionTokens": 0},
        "isContinued": False,
    })
    yield f"e:{finish_event}\n"

    # Send done event
    done_event = json.dumps({
        "finishReason": "stop",
        "usage": {"promptTokens": 0, "completionTokens": 0},
    })
    yield f"d:{done_event}\n"


@router.post(
    "/stream",
    summary="Stream Chat Response",
    description="""
Stream an AI-generated response to a chat conversation.

This endpoint accepts a list of messages in Vercel AI SDK format and returns
a Server-Sent Events (SSE) stream of response chunks. Each chunk contains
a portion of the AI's response, allowing for real-time streaming display.

**Session Management:**
Include the `X-Session-ID` header to maintain conversation history across
multiple requests. If not provided, a new session is created. The session_id
in the request body is also supported for backwards compatibility.

**SSE Format:**
- Each chunk: `data: {"content": "token"}\\n\\n`
- End signal: `data: [DONE]\\n\\n`

**Vercel AI SDK Compatibility:**
This endpoint is designed to work with the `useChat` hook from the
Vercel AI SDK, which handles SSE parsing automatically.
    """,
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "SSE stream of chat response chunks",
            "content": {
                "text/event-stream": {
                    "example": 'data: {"content": "Hello"}\n\ndata: {"content": " there"}\n\ndata: [DONE]\n\n'
                }
            },
        },
        422: {
            "description": "Validation error - invalid request format",
        },
    },
    status_code=status.HTTP_200_OK,
)
async def chat_stream(
    request: ChatRequest,
    x_session_id: str | None = Header(
        default=None,
        description="Session ID for conversation history. If not provided, uses request body session_id or creates new session.",
        alias="X-Session-ID",
    ),
) -> StreamingResponse:
    """
    Stream a chat response via Server-Sent Events.

    Accepts a conversation history and streams back the AI response
    token by token. Compatible with Vercel AI SDK's useChat hook.

    Args:
        request: ChatRequest containing the message history and optional session_id.
        x_session_id: Session ID from X-Session-ID header for conversation history.

    Returns:
        StreamingResponse with SSE media type containing response chunks.

    Raises:
        HTTPException: 422 if request validation fails.

    Example:
        >>> # curl example
        >>> # curl -X POST http://localhost:8000/api/v1/chat/stream \\
        >>> #   -H "Content-Type: application/json" \\
        >>> #   -H "X-Session-ID: abc123" \\
        >>> #   -d '{"messages": [{"role": "user", "content": "Hello"}]}'
    """
    # Header takes precedence, then body, then generate new
    session_id = x_session_id or request.session_id or str(uuid.uuid4())

    return StreamingResponse(
        _generate_stream(request, session_id),
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "X-Vercel-AI-Data-Stream": "v1",  # Required for Vercel AI SDK
        },
    )

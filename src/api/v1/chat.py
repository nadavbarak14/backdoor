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

import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse

from src.schemas.chat import ChatChunk, ChatRequest
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
) -> AsyncGenerator[str, None]:
    """
    Generate streaming response from the LLM.

    Wraps the ChatService stream method to format output as SSE events
    compatible with Vercel AI SDK.

    Args:
        request: The chat request containing conversation messages.

    Yields:
        SSE-formatted string chunks.

    Example:
        >>> async for chunk in _generate_stream(request):
        ...     print(chunk)
        data: {"content": "Hello"}
        data: {"content": " there"}
        ...
    """
    chat_service = get_chat_service()

    # Generate session ID if not provided
    session_id = request.session_id or str(uuid.uuid4())

    # Stream response from LLM
    async for content in chat_service.stream(request.messages, session_id):
        chunk = ChatChunk(content=content)
        yield f"data: {chunk.model_dump_json()}\n\n"

    # Signal stream completion
    yield "data: [DONE]\n\n"


@router.post(
    "/stream",
    summary="Stream Chat Response",
    description="""
Stream an AI-generated response to a chat conversation.

This endpoint accepts a list of messages in Vercel AI SDK format and returns
a Server-Sent Events (SSE) stream of response chunks. Each chunk contains
a portion of the AI's response, allowing for real-time streaming display.

**Session Management:**
Include a `session_id` in your request to maintain conversation history
across multiple requests. If not provided, a new session is created.

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
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """
    Stream a chat response via Server-Sent Events.

    Accepts a conversation history and streams back the AI response
    token by token. Compatible with Vercel AI SDK's useChat hook.

    Args:
        request: ChatRequest containing the message history and optional session_id.

    Returns:
        StreamingResponse with SSE media type containing response chunks.

    Raises:
        HTTPException: 422 if request validation fails.

    Example:
        >>> # curl example
        >>> # curl -X POST http://localhost:8000/api/v1/chat/stream \\
        >>> #   -H "Content-Type: application/json" \\
        >>> #   -d '{"messages": [{"role": "user", "content": "Hello"}], "session_id": "abc123"}'
    """
    return StreamingResponse(
        _generate_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )

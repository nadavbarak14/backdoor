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

from collections.abc import AsyncGenerator

from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse

from src.schemas.chat import ChatChunk, ChatRequest

router = APIRouter(prefix="/chat", tags=["Chat"])


async def _generate_placeholder_stream(
    request: ChatRequest,
) -> AsyncGenerator[str, None]:
    """
    Generate placeholder streaming response.

    This is a temporary implementation that echoes back the last user message.
    Will be replaced by LangChain chat service in Ticket 4.

    Args:
        request: The chat request containing conversation messages.

    Yields:
        SSE-formatted string chunks.

    Example:
        >>> async for chunk in _generate_placeholder_stream(request):
        ...     print(chunk)
        data: {"content": "You"}
        data: {"content": " said"}
        ...
    """
    # Get the last user message for the placeholder response
    last_user_message = ""
    for msg in reversed(request.messages):
        if msg.role == "user":
            last_user_message = msg.content
            break

    # Placeholder response - will be replaced by actual LLM in Ticket 4
    response_text = f"[Placeholder] You asked: {last_user_message}"

    # Simulate streaming by yielding word by word
    words = response_text.split(" ")
    for i, word in enumerate(words):
        # Add space before word (except first)
        content = f" {word}" if i > 0 else word
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
        request: ChatRequest containing the message history.

    Returns:
        StreamingResponse with SSE media type containing response chunks.

    Raises:
        HTTPException: 422 if request validation fails.

    Example:
        >>> # curl example
        >>> # curl -X POST http://localhost:8000/api/v1/chat/stream \\
        >>> #   -H "Content-Type: application/json" \\
        >>> #   -d '{"messages": [{"role": "user", "content": "Hello"}]}'
    """
    return StreamingResponse(
        _generate_placeholder_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )

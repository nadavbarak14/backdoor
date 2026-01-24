"""
Main Application Module

Entry point for the Basketball Analytics Platform FastAPI application.
Configures the app with middleware, routers, and startup/shutdown events.

Usage:
    # Development
    uv run uvicorn src.main:app --reload

    # Production
    uv run uvicorn src.main:app --host 0.0.0.0 --port 8000

Endpoints:
    - GET /health - Health check endpoint
    - /docs - Swagger UI documentation
    - /redoc - ReDoc documentation
    - /api/v1/* - API version 1 endpoints
"""

from fastapi import FastAPI

from src.api.v1.router import router as api_v1_router
from src.core import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="A comprehensive basketball analytics platform for tracking "
    "leagues, teams, players, and game statistics.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


@app.get(
    "/health",
    summary="Health Check",
    description="Returns the health status of the API. "
    "Use this endpoint for load balancer health checks.",
    tags=["Health"],
    response_description="Health status response",
)
def health_check() -> dict[str, str]:
    """
    Health check endpoint for monitoring and load balancers.

    Returns:
        dict with status key indicating the API is healthy.

    Example:
        >>> response = client.get("/health")
        >>> response.json()
        {"status": "healthy"}
    """
    return {"status": "healthy"}


# Include API v1 router
app.include_router(api_v1_router, prefix=settings.API_PREFIX)

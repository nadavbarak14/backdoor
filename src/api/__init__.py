"""
API Package

FastAPI routers and HTTP endpoint definitions.
The API layer handles HTTP logic and delegates to services.

Structure:
    - v1/: API version 1 endpoints

Usage:
    from src.api.v1.router import router as api_v1_router

    app.include_router(api_v1_router, prefix="/api/v1")
"""

from src.api.v1.router import router as api_v1_router

__all__ = ["api_v1_router"]

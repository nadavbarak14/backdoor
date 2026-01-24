"""
API Version 1 Package

Contains all endpoints for API version 1 under /api/v1/.

Routers:
    - leagues_router: League management endpoints
    - teams_router: Team management endpoints
    - players_router: Player management endpoints
    - router: Combined router with all v1 endpoints

Usage:
    from src.api.v1.router import router
    from src.api.v1 import leagues_router, teams_router, players_router
"""

from src.api.v1.leagues import router as leagues_router
from src.api.v1.players import router as players_router
from src.api.v1.router import router
from src.api.v1.teams import router as teams_router

__all__ = [
    "router",
    "leagues_router",
    "teams_router",
    "players_router",
]

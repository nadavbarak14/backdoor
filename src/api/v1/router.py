"""
API Version 1 Router Aggregator

Combines all v1 API routers into a single router for inclusion in the main app.
All endpoints are accessible under the /api/v1 prefix.

Routers included:
    - /leagues - League management endpoints
    - /teams - Team management endpoints
    - /players - Player management endpoints
    - /games - Game management endpoints
    - /stats - Statistics endpoints (league leaders)
    - /sync - Sync operation tracking endpoints

Usage:
    from src.api.v1.router import router as api_v1_router

    app.include_router(api_v1_router, prefix="/api/v1")
"""

from fastapi import APIRouter

from src.api.v1.games import router as games_router
from src.api.v1.leagues import router as leagues_router
from src.api.v1.players import router as players_router
from src.api.v1.stats import router as stats_router
from src.api.v1.sync import router as sync_router
from src.api.v1.teams import router as teams_router

router = APIRouter()

# Include all v1 routers
router.include_router(leagues_router)
router.include_router(teams_router)
router.include_router(players_router)
router.include_router(games_router)
router.include_router(stats_router)
router.include_router(sync_router)

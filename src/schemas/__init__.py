"""
Schemas Package

Pydantic models for API request validation and response serialization.
Schemas define the contract between the API and its clients.

This package provides:
- Base utilities (OrmBase, PaginatedResponse)
- League and Season schemas
- Team schemas
- Player schemas

Usage:
    from src.schemas import PlayerCreate, PlayerResponse, LeagueResponse
    from src.schemas.base import PaginatedResponse
"""

from src.schemas.base import OrmBase, PaginatedResponse
from src.schemas.league import (
    LeagueCreate,
    LeagueListResponse,
    LeagueResponse,
    LeagueUpdate,
    SeasonCreate,
    SeasonFilter,
    SeasonResponse,
    SeasonUpdate,
)
from src.schemas.player import (
    PlayerCreate,
    PlayerFilter,
    PlayerListResponse,
    PlayerResponse,
    PlayerTeamHistoryResponse,
    PlayerUpdate,
    PlayerWithHistoryResponse,
)
from src.schemas.team import (
    TeamCreate,
    TeamFilter,
    TeamListResponse,
    TeamResponse,
    TeamRosterPlayerResponse,
    TeamRosterResponse,
    TeamUpdate,
)

__all__ = [
    # Base utilities
    "OrmBase",
    "PaginatedResponse",
    # League schemas
    "LeagueCreate",
    "LeagueUpdate",
    "LeagueResponse",
    "LeagueListResponse",
    # Season schemas
    "SeasonCreate",
    "SeasonUpdate",
    "SeasonResponse",
    "SeasonFilter",
    # Team schemas
    "TeamCreate",
    "TeamUpdate",
    "TeamResponse",
    "TeamListResponse",
    "TeamFilter",
    "TeamRosterPlayerResponse",
    "TeamRosterResponse",
    # Player schemas
    "PlayerCreate",
    "PlayerUpdate",
    "PlayerResponse",
    "PlayerListResponse",
    "PlayerFilter",
    "PlayerTeamHistoryResponse",
    "PlayerWithHistoryResponse",
]

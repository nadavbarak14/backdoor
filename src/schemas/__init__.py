"""
Schemas Package

Pydantic models for API request validation and response serialization.
Schemas define the contract between the API and its clients.

This package provides:
- Base utilities (OrmBase, PaginatedResponse)
- League and Season schemas
- Team schemas
- Player schemas
- Game schemas
- Stats schemas (PlayerGameStats, TeamGameStats)
- Play-by-Play schemas
- Player Stats schemas (PlayerSeasonStats, LeagueLeaders)
- Sync schemas (SyncLog, SyncStatus)
- Chat schemas (ChatMessage, ChatRequest, ChatChunk)

Usage:
    from src.schemas import PlayerCreate, PlayerResponse, LeagueResponse
    from src.schemas import GameCreate, GameResponse, GameStatus
    from src.schemas.base import PaginatedResponse
"""

from src.schemas.analytics import (
    ClutchFilter,
    OpponentFilter,
    SituationalFilter,
    TimeFilter,
)
from src.schemas.base import OrmBase, PaginatedResponse
from src.schemas.chat import (
    ChatChunk,
    ChatMessage,
    ChatRequest,
)
from src.schemas.enums import EventType, GameStatus, Position
from src.schemas.game import (
    EventType,
    GameCreate,
    GameFilter,
    GameListResponse,
    GameResponse,
    GameStatus,
    GameUpdate,
    GameWithBoxScoreResponse,
    PlayerBoxScoreResponse,
    TeamBoxScoreResponse,
)
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
from src.schemas.play_by_play import (
    PlayByPlayEventResponse,
    PlayByPlayFilter,
    PlayByPlayResponse,
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
from src.schemas.player_stats import (
    LeagueLeaderEntry,
    LeagueLeadersFilter,
    LeagueLeadersResponse,
    PlayerCareerStatsResponse,
    PlayerSeasonStatsResponse,
    StatsCategory,
)
from src.schemas.search import (
    AutocompleteResponse,
    BrowseItem,
    BrowseParent,
    BrowseResponse,
    EntityType,
    SearchResult,
)
from src.schemas.stats import (
    PlayerGameLogResponse,
    PlayerGameStatsResponse,
    PlayerGameStatsWithGameResponse,
    TeamGameHistoryResponse,
    TeamGameStatsResponse,
    TeamGameSummaryResponse,
)
from src.schemas.sync import (
    SeasonSyncCoverage,
    SyncCoverageResponse,
    SyncLogFilter,
    SyncLogListResponse,
    SyncLogResponse,
    SyncSourceStatus,
    SyncStatus,
    SyncStatusResponse,
    SyncTriggerRequest,
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
    # Analytics schemas
    "ClutchFilter",
    "OpponentFilter",
    "SituationalFilter",
    "TimeFilter",
    # Chat schemas
    "ChatChunk",
    "ChatMessage",
    "ChatRequest",
    # Base utilities
    "OrmBase",
    "PaginatedResponse",
    # Domain enums
    "EventType",
    "GameStatus",
    "Position",
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
    # Game schemas
    "GameStatus",
    "EventType",
    "GameCreate",
    "GameUpdate",
    "GameResponse",
    "GameListResponse",
    "GameFilter",
    "GameWithBoxScoreResponse",
    "TeamBoxScoreResponse",
    "PlayerBoxScoreResponse",
    # Stats schemas
    "PlayerGameStatsResponse",
    "PlayerGameStatsWithGameResponse",
    "PlayerGameLogResponse",
    "TeamGameStatsResponse",
    "TeamGameSummaryResponse",
    "TeamGameHistoryResponse",
    # Play-by-Play schemas
    "PlayByPlayEventResponse",
    "PlayByPlayResponse",
    "PlayByPlayFilter",
    # Player stats schemas
    "StatsCategory",
    "PlayerSeasonStatsResponse",
    "PlayerCareerStatsResponse",
    "LeagueLeaderEntry",
    "LeagueLeadersResponse",
    "LeagueLeadersFilter",
    # Sync schemas
    "SyncStatus",
    "SyncLogResponse",
    "SyncLogListResponse",
    "SyncLogFilter",
    "SyncTriggerRequest",
    "SyncSourceStatus",
    "SyncStatusResponse",
    "SeasonSyncCoverage",
    "SyncCoverageResponse",
    # Search schemas
    "EntityType",
    "SearchResult",
    "AutocompleteResponse",
    "BrowseItem",
    "BrowseParent",
    "BrowseResponse",
]

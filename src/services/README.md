# Services

## Purpose

Business logic layer for the Basketball Analytics Platform. Services encapsulate all business rules, validation, and data orchestration. They sit between the API layer and data models, providing a clean separation of concerns.

## Contents

| File | Description |
|------|-------------|
| `__init__.py` | Public exports for all services |
| `base.py` | Generic BaseService with reusable CRUD operations |
| `league.py` | LeagueService and SeasonService |
| `team.py` | TeamService with roster and filtering |
| `player.py` | PlayerService with team history and filtering |
| `game.py` | GameService with box score loading and filtering |
| `stats.py` | PlayerGameStatsService and TeamGameStatsService |
| `play_by_play.py` | PlayByPlayService with event linking and shot charts |

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer                             │
│   (HTTP handling, request/response, authentication)      │
└───────────────────────┬─────────────────────────────────┘
                        │ Depends(get_db) → Session
                        ▼
┌─────────────────────────────────────────────────────────┐
│                  Service Layer                           │
│   (Business logic, validation, data orchestration)       │
│                                                          │
│  ┌───────────────┐  ┌───────────────┐  ┌──────────────┐ │
│  │ LeagueService │  │  TeamService  │  │PlayerService │ │
│  └───────────────┘  └───────────────┘  └──────────────┘ │
│  ┌───────────────┐  ┌───────────────┐  ┌──────────────┐ │
│  │ SeasonService │  │  GameService  │  │PlayByPlay-   │ │
│  └───────────────┘  └───────────────┘  │    Service   │ │
│  ┌────────────────────────┐            └──────────────┘ │
│  │ PlayerGameStatsService │  ... extends BaseService[T] │
│  │ TeamGameStatsService   │                             │
│  └────────────────────────┘                             │
└───────────────────────┬─────────────────────────────────┘
                        │ SQLAlchemy ORM
                        ▼
┌─────────────────────────────────────────────────────────┐
│                   Data Layer                             │
│         (SQLAlchemy models, database)                    │
└─────────────────────────────────────────────────────────┘
```

## Service Reference

### BaseService[ModelT]

Generic base class providing common CRUD operations for any model.

```python
from src.services.base import BaseService
from src.models import Player

class PlayerService(BaseService[Player]):
    def __init__(self, db: Session):
        super().__init__(db, Player)
```

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_by_id` | `(id: UUID) -> ModelT \| None` | Get entity by primary key |
| `get_all` | `(skip=0, limit=100) -> list[ModelT]` | Paginated list of all entities |
| `count` | `() -> int` | Total count of entities |
| `create` | `(data: dict) -> ModelT` | Create new entity from dict |
| `update` | `(id: UUID, data: dict) -> ModelT \| None` | Update entity, returns None if not found |
| `delete` | `(id: UUID) -> bool` | Delete entity, returns success status |

### LeagueService

Extends BaseService with league-specific operations.

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_by_code` | `(code: str) -> League \| None` | Find league by unique code (e.g., "NBA") |
| `get_with_season_count` | `(league_id: UUID) -> tuple[League \| None, int]` | Get league with season count |
| `get_all_with_season_counts` | `(skip=0, limit=100) -> list[tuple[League, int]]` | All leagues with counts |
| `create_league` | `(data: LeagueCreate) -> League` | Create from Pydantic schema |
| `update_league` | `(league_id: UUID, data: LeagueUpdate) -> League \| None` | Update from schema |

### SeasonService

Extends BaseService with season-specific operations.

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_by_league` | `(league_id: UUID, skip=0, limit=100) -> list[Season]` | All seasons for a league |
| `get_current` | `(league_id: UUID \| None = None) -> Season \| None` | Get current active season |
| `create_season` | `(data: SeasonCreate) -> Season` | Create with is_current handling |
| `set_current` | `(season_id: UUID) -> Season \| None` | Mark season as current (unsets others) |
| `update_season` | `(season_id: UUID, data: SeasonUpdate) -> Season \| None` | Update from schema |

**Note:** When creating or updating a season with `is_current=True`, other seasons in the same league are automatically set to `is_current=False`.

### TeamService

Extends BaseService with team-specific operations.

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_filtered` | `(filter_params: TeamFilter, skip=0, limit=100) -> tuple[list[Team], int]` | Filtered teams with total |
| `get_by_external_id` | `(source: str, external_id: str) -> Team \| None` | Find by external provider ID |
| `get_roster` | `(team_id: UUID, season_id: UUID) -> list[PlayerTeamHistory]` | Team roster for season |
| `create_team` | `(data: TeamCreate) -> Team` | Create from Pydantic schema |
| `update_team` | `(team_id: UUID, data: TeamUpdate) -> Team \| None` | Update from schema |
| `add_to_season` | `(team_id: UUID, season_id: UUID) -> TeamSeason \| None` | Associate team with season |

### PlayerService

Extends BaseService with player-specific operations.

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_with_history` | `(player_id: UUID) -> Player \| None` | Player with team_histories eager loaded |
| `get_filtered` | `(filter_params: PlayerFilter, skip=0, limit=100) -> tuple[list[Player], int]` | Filtered players with total |
| `get_by_external_id` | `(source: str, external_id: str) -> Player \| None` | Find by external provider ID |
| `create_player` | `(data: PlayerCreate) -> Player` | Create from Pydantic schema |
| `update_player` | `(player_id: UUID, data: PlayerUpdate) -> Player \| None` | Update from schema |
| `add_to_team` | `(player_id, team_id, season_id, jersey_number?, position?) -> PlayerTeamHistory \| None` | Add player to team roster |
| `get_team_history` | `(player_id: UUID) -> list[PlayerTeamHistory]` | All team history entries |

### GameService

Extends BaseService with game-specific operations.

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_with_box_score` | `(game_id: UUID) -> Game \| None` | Game with all stats eager loaded |
| `get_filtered` | `(filter_params: GameFilter, skip=0, limit=50) -> tuple[list[Game], int]` | Filtered games with total |
| `get_by_team` | `(team_id: UUID, season_id?: UUID, skip=0, limit=50) -> tuple[list[Game], int]` | Games for a team |
| `get_by_external_id` | `(source: str, external_id: str) -> Game \| None` | Find by external provider ID |
| `create_game` | `(data: GameCreate) -> Game` | Create from Pydantic schema |
| `update_game` | `(game_id: UUID, data: GameUpdate) -> Game \| None` | Update from schema |
| `update_score` | `(game_id: UUID, home_score: int, away_score: int, status?) -> Game \| None` | Update score and status |

### PlayerGameStatsService

Extends BaseService with player game statistics operations.

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_by_game` | `(game_id: UUID) -> list[PlayerGameStats]` | All player stats for a game |
| `get_by_game_and_team` | `(game_id: UUID, team_id: UUID) -> list[PlayerGameStats]` | Player stats for one team in game |
| `get_player_game_log` | `(player_id: UUID, season_id?: UUID, skip=0, limit=50) -> tuple[list, int]` | Player's game log with context |
| `get_by_player_and_game` | `(player_id: UUID, game_id: UUID) -> PlayerGameStats \| None` | Stats for specific player/game |
| `create_stats` | `(data: dict) -> PlayerGameStats` | Create stats entry |
| `bulk_create` | `(stats_list: list[dict]) -> list[PlayerGameStats]` | Bulk create for sync efficiency |
| `update_stats` | `(game_id: UUID, player_id: UUID, data: dict) -> PlayerGameStats \| None` | Update stats |

### TeamGameStatsService

Service for team game statistics (uses composite primary key, not BaseService).

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_by_game` | `(game_id: UUID) -> list[TeamGameStats]` | Both team stats for a game |
| `get_by_team_and_game` | `(team_id: UUID, game_id: UUID) -> TeamGameStats \| None` | Stats for specific team/game |
| `get_team_game_history` | `(team_id: UUID, season_id?: UUID, skip=0, limit=50) -> tuple[list, int]` | Team's game history |
| `create_stats` | `(data: dict) -> TeamGameStats` | Create team stats entry |
| `update_stats` | `(game_id: UUID, team_id: UUID, data: dict) -> TeamGameStats \| None` | Update stats |
| `calculate_from_player_stats` | `(game_id: UUID, team_id: UUID) -> TeamGameStats \| None` | Aggregate team stats from players |

### PlayByPlayService

Extends BaseService with play-by-play event operations.

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_by_game` | `(game_id: UUID, filter_params?: PlayByPlayFilter) -> list[PlayByPlayEvent]` | Events for a game |
| `get_with_related` | `(event_id: UUID) -> PlayByPlayEvent \| None` | Event with linked events loaded |
| `create_event` | `(data: dict) -> PlayByPlayEvent` | Create single event |
| `update_event` | `(event_id: UUID, data: dict) -> PlayByPlayEvent \| None` | Update event |
| `link_events` | `(event_id: UUID, related_event_ids: list[UUID]) -> None` | Link events together |
| `unlink_events` | `(event_id: UUID, related_event_ids: list[UUID]) -> None` | Remove event links |
| `get_related_events` | `(event_id: UUID) -> list[PlayByPlayEvent]` | Events this event links to |
| `get_events_linking_to` | `(event_id: UUID) -> list[PlayByPlayEvent]` | Events that link to this event |
| `bulk_create_with_links` | `(events: list[dict], links: list[tuple]) -> list[PlayByPlayEvent]` | Bulk create with relationships |
| `get_shot_chart_data` | `(game_id: UUID, team_id?: UUID, player_id?: UUID) -> list[PlayByPlayEvent]` | Shot events with coordinates |
| `get_events_by_type` | `(game_id: UUID, event_type: str, event_subtype?: str) -> list[PlayByPlayEvent]` | Events of specific type |
| `count_by_game` | `(game_id: UUID) -> int` | Total events in game |
| `delete_by_game` | `(game_id: UUID) -> int` | Delete all events for game |

## Filter Parameters

### TeamFilter

| Parameter | Type | Description |
|-----------|------|-------------|
| `league_id` | UUID \| None | Filter by teams in seasons of this league |
| `season_id` | UUID \| None | Filter by teams in this specific season |
| `country` | str \| None | Exact match on team country |
| `search` | str \| None | Case-insensitive search in name or short_name |

**Search behavior:** Matches if search term appears anywhere in `name` OR `short_name`.

```python
# Example: Find all USA teams with "Lakers" in name
filters = TeamFilter(country="USA", search="Lakers")
teams, total = team_service.get_filtered(filters)
```

### PlayerFilter

| Parameter | Type | Description |
|-----------|------|-------------|
| `team_id` | UUID \| None | Filter by players on this team (any season) |
| `season_id` | UUID \| None | Filter by players active in this season |
| `position` | str \| None | Exact match on player position |
| `nationality` | str \| None | Exact match on player nationality |
| `search` | str \| None | Case-insensitive search in first_name or last_name |

**Search behavior:** Matches if search term appears anywhere in `first_name` OR `last_name`.

```python
# Example: Find all point guards from USA
filters = PlayerFilter(position="PG", nationality="USA")
players, total = player_service.get_filtered(filters)

# Example: Search for players with "curry" in name
filters = PlayerFilter(search="curry")
players, total = player_service.get_filtered(filters)
```

### GameFilter

| Parameter | Type | Description |
|-----------|------|-------------|
| `season_id` | UUID \| None | Filter by games in this season |
| `team_id` | UUID \| None | Filter by team (home or away) |
| `start_date` | date \| None | Filter games on or after this date |
| `end_date` | date \| None | Filter games on or before this date |
| `status` | GameStatus \| None | Filter by game status (SCHEDULED, LIVE, FINAL, etc.) |

```python
# Example: Get all completed Lakers games in January 2024
from datetime import date
from src.schemas.game import GameFilter, GameStatus

filters = GameFilter(
    team_id=lakers_uuid,
    start_date=date(2024, 1, 1),
    end_date=date(2024, 1, 31),
    status=GameStatus.FINAL
)
games, total = game_service.get_filtered(filters)
```

### PlayByPlayFilter

| Parameter | Type | Description |
|-----------|------|-------------|
| `period` | int \| None | Filter by period number (1-4, 5+ for OT) |
| `event_type` | str \| None | Filter by event type (SHOT, REBOUND, etc.) |
| `player_id` | UUID \| None | Filter by player UUID |
| `team_id` | UUID \| None | Filter by team UUID |

```python
# Example: Get all 4th quarter shots by a specific player
from src.schemas.play_by_play import PlayByPlayFilter

filters = PlayByPlayFilter(
    period=4,
    event_type="SHOT",
    player_id=curry_uuid
)
events = play_by_play_service.get_by_game(game_id, filters)
```

## Usage Examples

### Basic CRUD Operations

```python
from src.services import LeagueService
from src.schemas import LeagueCreate, LeagueUpdate

service = LeagueService(db)

# Create
league = service.create_league(
    LeagueCreate(name="NBA", code="NBA", country="USA")
)

# Read
league = service.get_by_id(league_id)
all_leagues = service.get_all(skip=0, limit=10)
total = service.count()

# Update
updated = service.update_league(
    league_id,
    LeagueUpdate(name="National Basketball Association")
)

# Delete
success = service.delete(league_id)
```

### Using in API Endpoints

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.core import get_db
from src.services import PlayerService
from src.schemas import PlayerFilter, PlayerListResponse, PlayerResponse

router = APIRouter()

@router.get("/players", response_model=PlayerListResponse)
def list_players(
    position: str | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    service = PlayerService(db)
    filters = PlayerFilter(position=position, search=search)
    players, total = service.get_filtered(filters, skip=skip, limit=limit)

    return PlayerListResponse(
        items=[PlayerResponse.model_validate(p) for p in players],
        total=total
    )

@router.get("/players/{player_id}", response_model=PlayerResponse)
def get_player(player_id: UUID, db: Session = Depends(get_db)):
    service = PlayerService(db)
    player = service.get_by_id(player_id)

    if player is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player with id {player_id} not found"
        )

    return PlayerResponse.model_validate(player)
```

### Working with External IDs

```python
from src.services import PlayerService, TeamService

player_service = PlayerService(db)
team_service = TeamService(db)

# Find entities by external provider ID
lebron = player_service.get_by_external_id("nba", "2544")
lakers = team_service.get_by_external_id("nba", "1610612747")

# Useful for data synchronization from external APIs
if lebron is None:
    lebron = player_service.create_player(
        PlayerCreate(
            first_name="LeBron",
            last_name="James",
            external_ids={"nba": "2544"}
        )
    )
```

### Managing Team Rosters

```python
from src.services import PlayerService, TeamService

player_service = PlayerService(db)
team_service = TeamService(db)

# Add player to team for a season
player_service.add_to_team(
    player_id=lebron.id,
    team_id=lakers.id,
    season_id=current_season.id,
    jersey_number=23,
    position="SF"
)

# Get team roster
roster = team_service.get_roster(lakers.id, current_season.id)
for entry in roster:
    print(f"#{entry.jersey_number} {entry.player.full_name} ({entry.position})")

# Get player's team history
history = player_service.get_team_history(lebron.id)
for entry in history:
    print(f"{entry.season.name}: {entry.team.name}")
```

## Design Principles

1. **Single Responsibility**: Each service handles one entity/domain
2. **No HTTP Logic**: Services don't know about HTTP (no status codes, headers, etc.)
3. **Transaction Boundaries**: Services manage their own database transactions
4. **Testability**: Services can be tested with mock database sessions
5. **Generic Base**: Common CRUD operations in BaseService reduce duplication
6. **Type Safety**: Full type hints with generics for IDE support

## Dependencies

- **Internal**: `src/core/`, `src/models/`, `src/schemas/`
- **External**: `sqlalchemy`

## Related Documentation

- [Models](../models/README.md) - Database models
- [Schemas](../schemas/README.md) - Request/response validation
- [API Layer](../api/README.md) - HTTP endpoint definitions

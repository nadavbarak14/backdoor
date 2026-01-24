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
│  ┌───────────────┐                                       │
│  │ SeasonService │  ... extends BaseService[T] ...      │
│  └───────────────┘                                       │
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

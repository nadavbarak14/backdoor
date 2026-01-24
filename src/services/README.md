# Services

## Purpose

This directory contains the business logic layer for the Basketball Analytics Platform. Services sit between the API layer and data models, encapsulating all business rules, validation, and orchestration logic.

## Contents

| File | Description |
|------|-------------|
| `__init__.py` | Public exports for all services |
| `base.py` | Generic BaseService with reusable CRUD operations |
| `league.py` | LeagueService and SeasonService for league/season operations |
| `team.py` | TeamService for team operations including roster management |
| `player.py` | PlayerService for player operations including team history |
| `game.py` | Game business logic (future) |
| `stats.py` | Statistics calculations (future) |

## Service Classes

### BaseService[ModelT]

Generic base class providing common CRUD operations:

```python
from src.services.base import BaseService
from src.models.player import Player

class PlayerService(BaseService[Player]):
    def __init__(self, db: Session):
        super().__init__(db, Player)
```

**Methods:**
- `get_by_id(id: UUID) -> ModelT | None` - Get entity by UUID
- `get_all(skip, limit) -> list[ModelT]` - Paginated list
- `count() -> int` - Total count
- `create(data: dict) -> ModelT` - Create new entity
- `update(id, data: dict) -> ModelT | None` - Update entity
- `delete(id: UUID) -> bool` - Delete entity

### LeagueService

Extends BaseService with league-specific methods:

```python
from src.services import LeagueService

service = LeagueService(db)
nba = service.get_by_code("NBA")
league, count = service.get_with_season_count(league_id)
leagues_with_counts = service.get_all_with_season_counts()
```

**Methods:**
- `get_by_code(code: str)` - Find league by unique code
- `get_with_season_count(league_id)` - Returns (league, season_count)
- `get_all_with_season_counts()` - All leagues with counts
- `create_league(data: LeagueCreate)` - Create from schema
- `update_league(league_id, data: LeagueUpdate)` - Update from schema

### SeasonService

Extends BaseService with season-specific methods:

```python
from src.services import SeasonService

service = SeasonService(db)
seasons = service.get_by_league(league_id)
current = service.get_current(league_id)
service.set_current(season_id)  # Unsets other seasons in league
```

**Methods:**
- `get_by_league(league_id, skip, limit)` - Seasons for a league
- `get_current(league_id: UUID | None)` - Current active season
- `create_season(data: SeasonCreate)` - Create with is_current handling
- `set_current(season_id)` - Mark as current (unsets others)
- `update_season(season_id, data: SeasonUpdate)` - Update from schema

### TeamService

Extends BaseService with team-specific methods:

```python
from src.services import TeamService
from src.schemas.team import TeamFilter

service = TeamService(db)
teams, total = service.get_filtered(TeamFilter(country="USA"), skip=0, limit=20)
team = service.get_by_external_id("nba", "1610612747")
roster = service.get_roster(team_id, season_id)
```

**Methods:**
- `get_filtered(filter_params, skip, limit)` - Returns (teams, total)
- `get_by_external_id(source, external_id)` - Find by external ID
- `get_roster(team_id, season_id)` - PlayerTeamHistory with player loaded
- `create_team(data: TeamCreate)` - Create from schema
- `update_team(team_id, data: TeamUpdate)` - Update from schema
- `add_to_season(team_id, season_id)` - Create TeamSeason entry

### PlayerService

Extends BaseService with player-specific methods:

```python
from src.services import PlayerService
from src.schemas.player import PlayerFilter

service = PlayerService(db)
player = service.get_with_history(player_id)  # Eager loads team_histories
players, total = service.get_filtered(PlayerFilter(position="PG"), skip=0, limit=20)
player = service.get_by_external_id("nba", "2544")
history = service.get_team_history(player_id)
```

**Methods:**
- `get_with_history(player_id)` - Player with team_histories loaded
- `get_filtered(filter_params, skip, limit)` - Returns (players, total)
- `get_by_external_id(source, external_id)` - Find by external ID
- `create_player(data: PlayerCreate)` - Create from schema
- `update_player(player_id, data: PlayerUpdate)` - Update from schema
- `add_to_team(player_id, team_id, season_id, jersey_number, position)` - Create history
- `get_team_history(player_id)` - All PlayerTeamHistory entries

## Usage in API Endpoints

```python
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.services import LeagueService, PlayerService
from src.schemas.league import LeagueCreate, LeagueResponse

@router.post("/leagues", response_model=LeagueResponse)
def create_league(
    data: LeagueCreate,
    db: Session = Depends(get_db)
):
    service = LeagueService(db)
    league = service.create_league(data)
    return LeagueResponse.model_validate(league)

@router.get("/players/{player_id}")
def get_player(
    player_id: UUID,
    db: Session = Depends(get_db)
):
    service = PlayerService(db)
    player = service.get_by_id(player_id)
    if not player:
        raise HTTPException(404, "Player not found")
    return player
```

## Principles

1. **Single Responsibility**: Each service handles one entity/domain
2. **No HTTP Logic**: Services don't know about HTTP (no status codes, headers)
3. **Transaction Boundaries**: Services manage their own transactions
4. **Testability**: Services can be tested with mock database sessions
5. **Generic Base**: Common CRUD operations in BaseService
6. **Type Safety**: Full type hints with generics

## Dependencies

- **Internal**: `src/core/`, `src/models/`, `src/schemas/`
- **External**: `sqlalchemy`

## Related Documentation

- [Models](../models/README.md)
- [Schemas](../schemas/README.md)
- [API Layer](../api/README.md)

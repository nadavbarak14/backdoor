# API Version 1

## Purpose

Version 1 of the Basketball Analytics API. Contains all REST endpoints under `/api/v1/` for managing leagues, teams, players, and games.

## Contents

| File | Description |
|------|-------------|
| `__init__.py` | Package exports for all routers |
| `router.py` | Main router aggregating all v1 endpoints |
| `leagues.py` | League and season endpoints |
| `teams.py` | Team, roster, and game history endpoints |
| `players.py` | Player search, detail, game log, and stats endpoints |
| `games.py` | Game, box score, and play-by-play endpoints |
| `stats.py` | League leaders endpoints |
| `sync.py` | Sync operation tracking endpoints |

## Endpoint Summary

### Leagues (`/api/v1/leagues`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/leagues` | List all leagues with season counts |
| GET | `/leagues/{league_id}` | Get league by ID |
| GET | `/leagues/{league_id}/seasons` | List seasons for a league |

### Teams (`/api/v1/teams`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/teams` | List teams with optional filters |
| GET | `/teams/{team_id}` | Get team by ID |
| GET | `/teams/{team_id}/roster` | Get team roster for a season |
| GET | `/teams/{team_id}/games` | Get team game history |

### Players (`/api/v1/players`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/players` | Search players with filters |
| GET | `/players/{player_id}` | Get player with team history |
| GET | `/players/{player_id}/games` | Get player game log |
| GET | `/players/{player_id}/stats` | Get player career stats |
| GET | `/players/{player_id}/stats/{season_id}` | Get player season stats |

### Games (`/api/v1/games`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/games` | List games with filters |
| GET | `/games/{game_id}` | Get game with box score |
| GET | `/games/{game_id}/pbp` | Get play-by-play events |

### Stats (`/api/v1/stats`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/stats/leaders` | Get league leaders by category |

### Sync (`/api/v1/sync`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/sync/logs` | Get sync operation history |

## Query Parameters

### Pagination (All List Endpoints)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | int | 0 | Number of records to skip |
| `limit` | int | 100 | Maximum records to return (max: 1000) |

### Team Filters (`GET /teams`)

| Parameter | Type | Description |
|-----------|------|-------------|
| `league_id` | UUID | Filter by league |
| `season_id` | UUID | Filter by season participation |
| `country` | string | Filter by country |
| `search` | string | Search by team name |

### Player Filters (`GET /players`)

| Parameter | Type | Description |
|-----------|------|-------------|
| `team_id` | UUID | Filter by team |
| `season_id` | UUID | Filter by season participation |
| `position` | string | Filter by position (PG, SG, SF, PF, C) |
| `nationality` | string | Filter by nationality |
| `search` | string | Search by player name |

### Roster Parameters (`GET /teams/{id}/roster`)

| Parameter | Type | Description |
|-----------|------|-------------|
| `season_id` | UUID | Season ID (optional, defaults to current season) |

### Game Filters (`GET /games`)

| Parameter | Type | Description |
|-----------|------|-------------|
| `season_id` | UUID | Filter by season |
| `team_id` | UUID | Filter by team (home or away) |
| `start_date` | date | Filter games on or after this date |
| `end_date` | date | Filter games on or before this date |
| `status` | string | Filter by status (SCHEDULED, LIVE, FINAL, POSTPONED, CANCELLED) |

### Play-by-Play Filters (`GET /games/{id}/pbp`)

| Parameter | Type | Description |
|-----------|------|-------------|
| `period` | integer | Filter by period number (1-4, 5+ for OT) |
| `event_type` | string | Filter by event type (SHOT, REBOUND, etc.) |
| `player_id` | UUID | Filter by player |
| `team_id` | UUID | Filter by team |

### Game Log/History Parameters

Used by both `/players/{id}/games` and `/teams/{id}/games`:

| Parameter | Type | Description |
|-----------|------|-------------|
| `season_id` | UUID | Filter by season |

## Error Responses

All endpoints return consistent error responses:

| Status Code | Description | Response Body |
|-------------|-------------|---------------|
| 404 | Resource not found | `{"detail": "Resource with id {id} not found"}` |
| 422 | Validation error | `{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}` |

### Error Examples

```json
// 404 Not Found
{
    "detail": "League with id 550e8400-e29b-41d4-a716-446655440000 not found"
}

// 422 Validation Error
{
    "detail": [
        {
            "loc": ["query", "skip"],
            "msg": "value is not a valid integer",
            "type": "type_error.integer"
        }
    ]
}
```

## Usage

### Including in FastAPI App

```python
from fastapi import FastAPI
from src.api.v1.router import router as api_v1_router
from src.core import settings

app = FastAPI()
app.include_router(api_v1_router, prefix=settings.API_PREFIX)
```

### Creating a New Endpoint

```python
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.core import get_db
from src.schemas import PlayerResponse
from src.services import PlayerService

router = APIRouter(prefix="/players", tags=["Players"])

@router.get(
    "/{player_id}",
    response_model=PlayerResponse,
    summary="Get Player",
    description="Retrieve a player by ID.",
    responses={404: {"description": "Player not found"}}
)
def get_player(
    player_id: UUID,
    db: Session = Depends(get_db)
) -> PlayerResponse:
    """Get player by ID with full details."""
    service = PlayerService(db)
    player = service.get_by_id(player_id)

    if player is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player with id {player_id} not found"
        )

    return PlayerResponse.model_validate(player)
```

## Versioning Strategy

- **Breaking changes** require a new API version (v2)
- **Non-breaking additions** can be made to existing version
- **Deprecation period**: Old versions remain available for minimum 6 months

## Interactive Documentation

When running the server, access:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Dependencies

- **Internal**: `src/core/`, `src/schemas/`, `src/services/`
- **External**: `fastapi`

## Related Documentation

- [Leagues API Reference](../../../docs/api/leagues.md)
- [Teams API Reference](../../../docs/api/teams.md)
- [Players API Reference](../../../docs/api/players.md)
- [Games API Reference](../../../docs/api/games.md)
- [Stats API Reference](../../../docs/api/stats.md)
- [Sync API Reference](../../../docs/api/sync.md)
- [Game Statistics Reference](../../../docs/models/game-stats.md)
- [Aggregated Stats Reference](../../../docs/models/aggregated-stats.md)
- [Play-by-Play Reference](../../../docs/models/play-by-play.md)
- [API Overview](../../../docs/api/README.md)
- [Schemas](../../schemas/README.md)
- [Services](../../services/README.md)

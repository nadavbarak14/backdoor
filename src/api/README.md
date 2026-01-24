# API

## Purpose

This directory contains FastAPI routers and HTTP endpoint definitions. The API layer handles HTTP request/response logic and delegates business operations to services.

## Contents

| File/Directory | Description |
|----------------|-------------|
| `__init__.py` | Public exports and main router |
| `deps.py` | Shared dependencies (auth, pagination) (future) |
| `v1/` | Version 1 API endpoints |

## Structure

```
api/
├── README.md
├── __init__.py
├── deps.py              # Shared dependencies
└── v1/
    ├── README.md
    ├── __init__.py
    ├── router.py        # Main v1 router (aggregates all)
    ├── players.py       # /api/v1/players endpoints
    ├── teams.py         # /api/v1/teams endpoints
    ├── games.py         # /api/v1/games endpoints
    └── stats.py         # /api/v1/stats endpoints
```

## Router Pattern

### Basic Router

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.schemas.player import PlayerCreate, PlayerResponse
from src.services.player import PlayerService

router = APIRouter(prefix="/players", tags=["Players"])

@router.get("/", response_model=list[PlayerResponse])
def list_players(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all players.

    Args:
        skip: Number of records to skip
        limit: Maximum records to return

    Returns:
        List of players
    """
    service = PlayerService(db)
    return service.get_all(skip=skip, limit=limit)

@router.post("/", response_model=PlayerResponse, status_code=201)
def create_player(
    data: PlayerCreate,
    db: Session = Depends(get_db)
):
    """Create a new player."""
    service = PlayerService(db)
    return service.create(data)

@router.get("/{player_id}", response_model=PlayerResponse)
def get_player(
    player_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a player by ID."""
    service = PlayerService(db)
    player = service.get_by_id(player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player
```

### Aggregating Routers

```python
# src/api/v1/router.py
from fastapi import APIRouter
from src.api.v1 import players, teams, games, stats

router = APIRouter(prefix="/api/v1")

router.include_router(players.router)
router.include_router(teams.router)
router.include_router(games.router)
router.include_router(stats.router)
```

## Principles

1. **Thin Layer**: Routes delegate to services, minimal logic
2. **HTTP Concerns Only**: Status codes, headers, serialization
3. **Consistent Responses**: Use response_model for all endpoints
4. **OpenAPI Docs**: All endpoints fully documented

## Response Codes

| Code | Usage |
|------|-------|
| 200 | Successful GET, PUT, PATCH |
| 201 | Successful POST (created) |
| 204 | Successful DELETE (no content) |
| 400 | Bad request (validation error) |
| 404 | Resource not found |
| 422 | Unprocessable entity (Pydantic validation) |
| 500 | Internal server error |

## Dependencies

- **Internal**: `src/core/`, `src/schemas/`, `src/services/`
- **External**: `fastapi`

## Related Documentation

- [API Reference](../../docs/api/README.md)
- [Services](../services/README.md)
- [Schemas](../schemas/README.md)

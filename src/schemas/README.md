# Schemas

## Purpose

This directory contains Pydantic models used for API request validation and response serialization. Schemas define the contract between the API and its clients.

## Contents

| File | Description |
|------|-------------|
| `__init__.py` | Public exports for all schemas |
| `base.py` | Shared schema utilities (OrmBase, PaginatedResponse) |
| `league.py` | League and Season request/response schemas |
| `team.py` | Team request/response schemas |
| `player.py` | Player request/response schemas |

## Schema Types

### Base Utilities (`base.py`)

| Schema | Description |
|--------|-------------|
| `OrmBase` | Base model with `from_attributes=True` for ORM compatibility |
| `PaginatedResponse[T]` | Generic paginated response wrapper |

### League Schemas (`league.py`)

| Schema | Description |
|--------|-------------|
| `LeagueCreate` | POST request body for creating a league |
| `LeagueUpdate` | PATCH request body for updating a league |
| `LeagueResponse` | League response with season_count |
| `LeagueListResponse` | Paginated list of leagues |
| `SeasonCreate` | POST request body for creating a season |
| `SeasonUpdate` | PATCH request body for updating a season |
| `SeasonResponse` | Season response |
| `SeasonFilter` | Query parameters for filtering seasons |

### Team Schemas (`team.py`)

| Schema | Description |
|--------|-------------|
| `TeamCreate` | POST request body for creating a team |
| `TeamUpdate` | PATCH request body for updating a team |
| `TeamResponse` | Team response |
| `TeamListResponse` | Paginated list of teams |
| `TeamFilter` | Query parameters for filtering teams |
| `TeamRosterPlayerResponse` | Player info in roster context |
| `TeamRosterResponse` | Team roster with players |

### Player Schemas (`player.py`)

| Schema | Description |
|--------|-------------|
| `PlayerCreate` | POST request body for creating a player |
| `PlayerUpdate` | PATCH request body for updating a player |
| `PlayerResponse` | Player response with full_name |
| `PlayerListResponse` | Paginated list of players |
| `PlayerFilter` | Query parameters for filtering players |
| `PlayerTeamHistoryResponse` | Team history entry |
| `PlayerWithHistoryResponse` | Player with full team history |

## Usage

### Request Validation

```python
from src.schemas import PlayerCreate

# Automatic validation in FastAPI
@router.post("/players", response_model=PlayerResponse)
def create_player(data: PlayerCreate, db: Session = Depends(get_db)):
    service = PlayerService(db)
    return service.create(data)
```

### Response Serialization

```python
from src.schemas import PlayerResponse

# Convert ORM object to response schema
player_orm = session.get(Player, player_id)
response = PlayerResponse.model_validate(player_orm)
```

### Query Filtering

```python
from src.schemas import PlayerFilter

@router.get("/players")
def list_players(
    filters: PlayerFilter = Depends(),
    db: Session = Depends(get_db)
):
    service = PlayerService(db)
    return service.list(filters)
```

### Paginated Responses

```python
from src.schemas.base import PaginatedResponse
from src.schemas import PlayerResponse

@router.get("/players", response_model=PaginatedResponse[PlayerResponse])
def list_players(page: int = 1, page_size: int = 20):
    ...
```

## Naming Conventions

| Suffix | Purpose | Example |
|--------|---------|---------|
| `Create` | POST request body | `PlayerCreate` |
| `Update` | PUT/PATCH request body | `PlayerUpdate` |
| `Response` | Single item response | `PlayerResponse` |
| `ListResponse` | List of items response | `PlayerListResponse` |
| `Filter` | Query parameters | `PlayerFilter` |

## Field Validation

Schemas use Pydantic v2 `Field()` for validation:

```python
# String length validation
name: str = Field(..., min_length=1, max_length=100)

# Numeric range validation
height_cm: int | None = Field(None, ge=100, le=250)

# Optional with default
is_current: bool = Field(default=False)
```

## Dependencies

- **Internal**: None (schemas are independent)
- **External**: `pydantic`

## Related Documentation

- [API Documentation](../../docs/api/README.md)
- [Models](../models/README.md)

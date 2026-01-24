# Schemas

## Purpose

Pydantic models for API request validation and response serialization. Schemas define the contract between the API and its clients, ensuring data integrity and type safety.

## Contents

| File | Description |
|------|-------------|
| `__init__.py` | Public exports for all schemas |
| `base.py` | Shared schema utilities (OrmBase, PaginatedResponse) |
| `league.py` | League and Season request/response schemas |
| `team.py` | Team request/response schemas |
| `player.py` | Player request/response schemas |

## Naming Conventions

| Suffix | Purpose | HTTP Methods | Example |
|--------|---------|--------------|---------|
| `Create` | Request body for creation | POST | `PlayerCreate` |
| `Update` | Request body for updates | PUT, PATCH | `PlayerUpdate` |
| `Response` | Single item response | GET, POST | `PlayerResponse` |
| `ListResponse` | List of items with total | GET (list) | `PlayerListResponse` |
| `Filter` | Query parameters | GET (list) | `PlayerFilter` |

## Schema Reference

### Base Utilities (`base.py`)

| Schema | Description |
|--------|-------------|
| `OrmBase` | Base model with `from_attributes=True` for ORM compatibility |
| `PaginatedResponse[T]` | Generic paginated response wrapper |

### League Schemas (`league.py`)

| Schema | Purpose | Fields |
|--------|---------|--------|
| `LeagueCreate` | Create league | name, code, country |
| `LeagueUpdate` | Update league | name?, code?, country? |
| `LeagueResponse` | League output | id, name, code, country, season_count, timestamps |
| `LeagueListResponse` | League list | items, total |
| `SeasonCreate` | Create season | league_id, name, start_date, end_date, is_current? |
| `SeasonUpdate` | Update season | name?, start_date?, end_date?, is_current? |
| `SeasonResponse` | Season output | id, league_id, name, dates, is_current, timestamps |
| `SeasonFilter` | Filter seasons | league_id?, is_current? |

### Team Schemas (`team.py`)

| Schema | Purpose | Fields |
|--------|---------|--------|
| `TeamCreate` | Create team | name, short_name, city, country, external_ids? |
| `TeamUpdate` | Update team | name?, short_name?, city?, country?, external_ids? |
| `TeamResponse` | Team output | id, name, short_name, city, country, external_ids, timestamps |
| `TeamListResponse` | Team list | items, total |
| `TeamFilter` | Filter teams | league_id?, season_id?, country?, search? |
| `TeamRosterPlayerResponse` | Player in roster | id, names, jersey_number?, position? |
| `TeamRosterResponse` | Team roster | team, season_id, season_name, players |

### Player Schemas (`player.py`)

| Schema | Purpose | Fields |
|--------|---------|--------|
| `PlayerCreate` | Create player | first_name, last_name, birth_date?, nationality?, height_cm?, position?, external_ids? |
| `PlayerUpdate` | Update player | first_name?, last_name?, birth_date?, nationality?, height_cm?, position?, external_ids? |
| `PlayerResponse` | Player output | id, names, full_name, birth_date, nationality, height_cm, position, external_ids, timestamps |
| `PlayerListResponse` | Player list | items, total |
| `PlayerFilter` | Filter players | team_id?, season_id?, position?, nationality?, search? |
| `PlayerTeamHistoryResponse` | Team history entry | team_id, team_name, season_id, season_name, jersey_number?, position? |
| `PlayerWithHistoryResponse` | Player + history | all PlayerResponse fields + team_history |

## Validation Rules

### String Length Constraints

| Schema | Field | Min | Max |
|--------|-------|-----|-----|
| LeagueCreate | name | 1 | 100 |
| LeagueCreate | code | 1 | 20 |
| LeagueCreate | country | 1 | 100 |
| SeasonCreate | name | 1 | 50 |
| TeamCreate | name | 1 | 100 |
| TeamCreate | short_name | 1 | 20 |
| TeamCreate | city | 1 | 100 |
| TeamCreate | country | 1 | 100 |
| PlayerCreate | first_name | 1 | 100 |
| PlayerCreate | last_name | 1 | 100 |
| PlayerCreate | nationality | - | 100 |
| PlayerCreate | position | - | 20 |
| PlayerFilter | search | 1 | - |
| TeamFilter | search | 1 | - |

### Numeric Constraints

| Schema | Field | Min | Max | Description |
|--------|-------|-----|-----|-------------|
| PlayerCreate | height_cm | 100 | 250 | Height in centimeters |

### Default Values

| Schema | Field | Default |
|--------|-------|---------|
| SeasonCreate | is_current | `False` |
| TeamCreate | external_ids | `None` |
| PlayerCreate | external_ids | `None` |
| PlayerResponse | external_ids | `{}` |
| TeamResponse | external_ids | `{}` |
| LeagueResponse | season_count | `0` |

## Usage Examples

### Request Validation (Create)

```python
from src.schemas import PlayerCreate

# FastAPI automatically validates request body
@router.post("/players", response_model=PlayerResponse)
def create_player(data: PlayerCreate, db: Session = Depends(get_db)):
    service = PlayerService(db)
    return service.create_player(data)

# Valid request
data = PlayerCreate(
    first_name="LeBron",
    last_name="James",
    birth_date=date(1984, 12, 30),
    nationality="USA",
    height_cm=206,
    position="SF",
    external_ids={"nba": "2544"}
)

# Invalid request - raises ValidationError
PlayerCreate(first_name="", last_name="James")  # first_name too short
PlayerCreate(first_name="LeBron", last_name="James", height_cm=300)  # height too large
```

### Request Validation (Update)

```python
from src.schemas import PlayerUpdate

# All fields are optional for partial updates
@router.patch("/players/{player_id}", response_model=PlayerResponse)
def update_player(
    player_id: UUID,
    data: PlayerUpdate,
    db: Session = Depends(get_db)
):
    service = PlayerService(db)
    return service.update_player(player_id, data)

# Only update position
data = PlayerUpdate(position="PF")
```

### Response Serialization

```python
from src.schemas import PlayerResponse, PlayerWithHistoryResponse

# Convert ORM object to response schema
player_orm = service.get_by_id(player_id)
response = PlayerResponse.model_validate(player_orm)

# With nested team history
player_with_history = service.get_with_history(player_id)
response = PlayerWithHistoryResponse(
    id=player.id,
    first_name=player.first_name,
    last_name=player.last_name,
    full_name=player.full_name,
    # ... other fields
    team_history=[
        PlayerTeamHistoryResponse(
            team_id=h.team_id,
            team_name=h.team.name,
            season_id=h.season_id,
            season_name=h.season.name,
            jersey_number=h.jersey_number,
            position=h.position
        )
        for h in player.team_histories
    ]
)
```

### Query Parameter Filtering

```python
from src.schemas import PlayerFilter

@router.get("/players", response_model=PlayerListResponse)
def list_players(
    team_id: UUID | None = Query(None),
    season_id: UUID | None = Query(None),
    position: str | None = Query(None),
    nationality: str | None = Query(None),
    search: str | None = Query(None, min_length=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    filters = PlayerFilter(
        team_id=team_id,
        season_id=season_id,
        position=position,
        nationality=nationality,
        search=search
    )
    service = PlayerService(db)
    players, total = service.get_filtered(filters, skip=skip, limit=limit)
    return PlayerListResponse(
        items=[PlayerResponse.model_validate(p) for p in players],
        total=total
    )
```

### List Response Structure

```python
from src.schemas import PlayerListResponse, PlayerResponse

# Response format for list endpoints
response = PlayerListResponse(
    items=[
        PlayerResponse(id=..., first_name="LeBron", ...),
        PlayerResponse(id=..., first_name="Stephen", ...),
    ],
    total=150  # Total count (not just items in this page)
)

# JSON output
{
    "items": [
        {"id": "...", "first_name": "LeBron", ...},
        {"id": "...", "first_name": "Stephen", ...}
    ],
    "total": 150
}
```

## Dependencies

- **Internal**: None (schemas are independent)
- **External**: `pydantic` v2

## Related Documentation

- [API Documentation](../../docs/api/README.md)
- [Models](../models/README.md)
- [Services](../services/README.md)

# Schemas

## Purpose

This directory contains Pydantic models used for API request validation and response serialization. Schemas define the contract between the API and its clients.

## Contents

| File | Description |
|------|-------------|
| `__init__.py` | Public exports |
| `base.py` | Shared schema utilities and base classes |
| `player.py` | Player request/response schemas (future) |
| `team.py` | Team request/response schemas (future) |
| `game.py` | Game request/response schemas (future) |
| `stats.py` | Statistics schemas (future) |

## Schema Patterns

### Request Schemas (Input)

Used for validating incoming API data:

```python
from pydantic import BaseModel, Field

class PlayerCreate(BaseModel):
    """Schema for creating a new player."""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    height_inches: int | None = Field(None, ge=48, le=96)

class PlayerUpdate(BaseModel):
    """Schema for updating a player (all fields optional)."""
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
```

### Response Schemas (Output)

Used for serializing database models to API responses:

```python
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class PlayerResponse(BaseModel):
    """Schema for player API response."""
    id: UUID
    first_name: str
    last_name: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### List Response Schemas

For paginated list endpoints:

```python
from typing import Generic, TypeVar

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int
```

## Usage

```python
from src.schemas.player import PlayerCreate, PlayerResponse

# In API endpoint
@router.post("/players", response_model=PlayerResponse)
def create_player(data: PlayerCreate, db: Session = Depends(get_db)):
    service = PlayerService(db)
    return service.create(data)
```

## Naming Conventions

| Suffix | Purpose | Example |
|--------|---------|---------|
| `Create` | POST request body | `PlayerCreate` |
| `Update` | PUT/PATCH request body | `PlayerUpdate` |
| `Response` | Single item response | `PlayerResponse` |
| `ListResponse` | List of items response | `PlayerListResponse` |
| `Filter` | Query parameters | `PlayerFilter` |

## Dependencies

- **Internal**: None (schemas are independent)
- **External**: `pydantic`

## Related Documentation

- [API Documentation](../../docs/api/README.md)
- [Models](../models/README.md)

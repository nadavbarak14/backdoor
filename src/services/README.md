# Services

## Purpose

This directory contains the business logic layer for the Basketball Analytics Platform. Services sit between the API layer and data models, encapsulating all business rules, validation, and orchestration logic.

## Contents

| File | Description |
|------|-------------|
| `__init__.py` | Public exports |
| `base.py` | Base service class with common operations |
| `player.py` | Player business logic (future) |
| `team.py` | Team business logic (future) |
| `game.py` | Game business logic (future) |
| `stats.py` | Statistics calculations (future) |

## Service Pattern

### Basic Service Structure

```python
from sqlalchemy.orm import Session
from src.models.player import Player
from src.schemas.player import PlayerCreate, PlayerUpdate

class PlayerService:
    """
    Business logic for player operations.

    Handles all player-related business rules, validation,
    and database operations.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, player_id: UUID) -> Player | None:
        """Get a player by ID."""
        return self.db.query(Player).filter(Player.id == player_id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[Player]:
        """Get all players with pagination."""
        return self.db.query(Player).offset(skip).limit(limit).all()

    def create(self, data: PlayerCreate) -> Player:
        """Create a new player."""
        player = Player(**data.model_dump())
        self.db.add(player)
        self.db.commit()
        self.db.refresh(player)
        return player

    def update(self, player_id: UUID, data: PlayerUpdate) -> Player | None:
        """Update an existing player."""
        player = self.get_by_id(player_id)
        if not player:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(player, field, value)
        self.db.commit()
        self.db.refresh(player)
        return player

    def delete(self, player_id: UUID) -> bool:
        """Delete a player."""
        player = self.get_by_id(player_id)
        if not player:
            return False
        self.db.delete(player)
        self.db.commit()
        return True
```

### Service with Business Logic

```python
class StatsService:
    """Statistics calculation service."""

    def __init__(self, db: Session):
        self.db = db

    def calculate_player_averages(self, player_id: UUID, season: str) -> dict:
        """
        Calculate per-game averages for a player.

        Business rules:
        - Only include games where player played > 0 minutes
        - Round averages to 1 decimal place
        - Return career averages if no season specified
        """
        # Business logic here
        pass
```

## Usage

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.services.player import PlayerService

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

## Dependencies

- **Internal**: `src/core/`, `src/models/`
- **External**: `sqlalchemy`

## Related Documentation

- [Models](../models/README.md)
- [API Layer](../api/README.md)

# Data Models

## Purpose

Documentation for the database schema and data models used in the Basketball Analytics Platform.

## Contents

| File | Description |
|------|-------------|
| `README.md` | This file - models overview |
| `game-stats.md` | Game statistics field reference |
| `play-by-play.md` | Play-by-play event types and linking |
| `aggregated-stats.md` | Aggregated season stats and sync tracking |
| `erd.md` | Entity relationship diagram (future) |
| `player.md` | Player model details (future) |
| `team.md` | Team model details (future) |
| `game.md` | Game model details (future) |

## Entity Overview

### Core Entities

| Entity | Description |
|--------|-------------|
| Player | Basketball player with bio and career info |
| Team | NBA team with franchise info |
| Season | NBA season (e.g., 2024-25) |
| Game | Individual game with date and teams |

### Statistics Entities

| Entity | Description |
|--------|-------------|
| PlayerGameStats | Per-game player statistics |
| TeamGameStats | Per-game team statistics |
| PlayerSeasonStats | Aggregated season stats |
| SyncLog | Sync operation tracking |

## Base Model Features

All models inherit from base classes providing:

### UUIDMixin
- `id`: UUID primary key, auto-generated

### TimestampMixin
- `created_at`: Record creation timestamp
- `updated_at`: Last modification timestamp

## Example Model

```python
from src.models.base import Base, UUIDMixin, TimestampMixin

class Player(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "players"

    first_name: Mapped[str]
    last_name: Mapped[str]
    birth_date: Mapped[date | None]
    height_inches: Mapped[int | None]
    weight_lbs: Mapped[int | None]
    position: Mapped[str | None]

    # Relationships
    stats: Mapped[list["PlayerGameStats"]] = relationship()
```

## Related Documentation

- [Source Models](../../src/models/README.md)
- [Migrations](../../alembic/README.md)

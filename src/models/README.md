# Models

## Purpose

Database models and mixins for the Basketball Analytics Platform. This module provides the SQLAlchemy declarative base and reusable mixins that all entity models inherit from.

## Contents

| File | Description |
|------|-------------|
| `__init__.py` | Package exports for Base, mixins, and all entity models |
| `base.py` | DeclarativeBase, UUIDMixin, and TimestampMixin |
| `league.py` | League and Season models |
| `team.py` | Team and TeamSeason models |
| `player.py` | Player and PlayerTeamHistory models |

## Usage

### Creating a New Model

All models should inherit from `Base` and include both `UUIDMixin` and `TimestampMixin`:

```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base, UUIDMixin, TimestampMixin


class Player(UUIDMixin, TimestampMixin, Base):
    """Player entity representing a basketball player."""

    __tablename__ = "players"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    jersey_number: Mapped[int | None] = mapped_column(nullable=True)
```

### What the Mixins Provide

#### UUIDMixin

Adds a UUID primary key column:

```python
id: Mapped[uuid.UUID]  # Auto-generated UUID4 on insert
```

#### TimestampMixin

Adds audit timestamp columns:

```python
created_at: Mapped[datetime]  # Set automatically on insert
updated_at: Mapped[datetime]  # Updated automatically on change
```

### Example Model with All Features

```python
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models import Base, UUIDMixin, TimestampMixin


class Team(UUIDMixin, TimestampMixin, Base):
    """
    Team entity representing a basketball team.

    Attributes:
        id: UUID primary key (from UUIDMixin)
        created_at: Creation timestamp (from TimestampMixin)
        updated_at: Last update timestamp (from TimestampMixin)
        name: Team name
        city: Team city
        players: Relationship to Player entities
    """

    __tablename__ = "teams"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    players: Mapped[list["Player"]] = relationship(back_populates="team")


class Player(UUIDMixin, TimestampMixin, Base):
    """Player entity with team relationship."""

    __tablename__ = "players"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("teams.id"),
        nullable=True,
    )

    # Relationships
    team: Mapped["Team | None"] = relationship(back_populates="players")
```

### Creating Tables

```python
from src.core.database import engine
from src.models import Base

# Create all tables
Base.metadata.create_all(bind=engine)
```

## Dependencies

### Internal Dependencies
- `src.core.config` - Settings for database configuration

### External Libraries
- `sqlalchemy` - ORM and database toolkit

## Inheritance Order

When creating models, the mixin order matters. Use this pattern:

```python
class MyModel(UUIDMixin, TimestampMixin, Base):
    ...
```

The mixins should come before `Base` to ensure their columns are properly added.

## Column Types

The mixins use the following SQLAlchemy types:

| Mixin | Column | Type | Notes |
|-------|--------|------|-------|
| UUIDMixin | id | UUID | Uses Python's uuid4 for generation |
| TimestampMixin | created_at | DateTime(timezone=True) | Server default to current time |
| TimestampMixin | updated_at | DateTime(timezone=True) | Auto-updates on modification |

## Related Documentation

- [Database Connection](../core/README.md) - Engine and session management
- [Architecture](../../docs/architecture.md) - System architecture overview

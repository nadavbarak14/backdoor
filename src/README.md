# Source Code

## Purpose

This directory contains all application source code for the Basketball Analytics Platform. Code is organized by **component layer** (models, schemas, services, api) for clear separation of concerns.

## Contents

| Directory | Description |
|-----------|-------------|
| `core/` | Core infrastructure: configuration, database connection, exceptions |
| `models/` | SQLAlchemy ORM models representing database tables |
| `schemas/` | Pydantic models for API request/response validation |
| `services/` | Business logic layer between API and data |
| `api/` | FastAPI routers and HTTP endpoints |
| `sync/` | External data synchronization (NBA API) |

## Architecture

```
                    ┌─────────────────────┐
                    │     HTTP Request    │
                    └──────────┬──────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                      API Layer (src/api/)                    │
│  Routes, request parsing, response formatting, auth         │
│  Uses: schemas (validation), services (logic)               │
└──────────────────────────────┬───────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                  Service Layer (src/services/)               │
│  Business logic, validation rules, orchestration            │
│  Uses: models (data access), core (database)                │
└──────────────────────────────┬───────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                   Model Layer (src/models/)                  │
│  SQLAlchemy ORM models, database table definitions          │
│  Uses: core (Base class, database engine)                   │
└──────────────────────────────┬───────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                    Core Layer (src/core/)                    │
│  Configuration, database connection, shared utilities       │
│  Uses: nothing (foundation layer)                           │
└──────────────────────────────────────────────────────────────┘
```

## Component Overview

### Core (`src/core/`)
Foundation layer with no dependencies on other src components.
- `config.py` - Application settings via Pydantic Settings
- `database.py` - SQLAlchemy engine and session management
- `exceptions.py` - Shared exception classes (future)

### Models (`src/models/`)
SQLAlchemy ORM models representing database tables.
- `base.py` - Base class, UUIDMixin, TimestampMixin
- `player.py` - Player model (future)
- `team.py` - Team model (future)
- `game.py` - Game model (future)

### Schemas (`src/schemas/`)
Pydantic models for API input validation and response serialization.
- `player.py` - PlayerCreate, PlayerUpdate, PlayerResponse (future)
- `team.py` - Team schemas (future)
- `game.py` - Game schemas (future)

### Services (`src/services/`)
Business logic layer. Contains validation rules and orchestrates data access.
- `player.py` - PlayerService with CRUD and business logic (future)
- `team.py` - TeamService (future)
- `game.py` - GameService (future)

### API (`src/api/`)
FastAPI routers organized by version.
- `v1/` - Version 1 API endpoints
- `deps.py` - Shared dependencies (auth, pagination) (future)

### Sync (`src/sync/`)
External API integrations for data import.
- `nba/` - NBA API client (future)

## Usage Examples

### Importing Components

```python
# Core - available everywhere
from src.core.config import settings
from src.core.database import get_db, SessionLocal

# Models - for database operations
from src.models.base import Base, UUIDMixin, TimestampMixin
from src.models.player import Player

# Schemas - for API validation
from src.schemas.player import PlayerCreate, PlayerResponse

# Services - for business logic
from src.services.player import PlayerService
```

### Creating a New Model

```python
# src/models/player.py
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from src.models.base import Base, UUIDMixin, TimestampMixin

class Player(UUIDMixin, TimestampMixin, Base):
    """Player entity representing a basketball player."""
    __tablename__ = "players"

    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
```

### Creating a Service

```python
# src/services/player.py
from sqlalchemy.orm import Session
from src.models.player import Player
from src.schemas.player import PlayerCreate

class PlayerService:
    """Business logic for player operations."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: PlayerCreate) -> Player:
        player = Player(**data.model_dump())
        self.db.add(player)
        self.db.commit()
        self.db.refresh(player)
        return player
```

## Dependencies

### Internal Dependency Graph

```
core/      → (no internal dependencies)
models/    → core/
schemas/   → (no internal dependencies, uses pydantic)
services/  → core/, models/
api/       → core/, models/, schemas/, services/
sync/      → core/, models/, services/
```

### External Libraries

| Library | Used By | Purpose |
|---------|---------|---------|
| SQLAlchemy | core/, models/ | ORM and database |
| Pydantic | core/, schemas/ | Validation and settings |
| FastAPI | api/ | Web framework |
| httpx | sync/ | HTTP client |

## Related Documentation

- [Development Guidelines](../CLAUDE.md)
- [Architecture Overview](../docs/architecture.md)
- [API Documentation](../docs/api/README.md)

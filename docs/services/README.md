# Services Documentation

## Purpose

This folder contains detailed documentation for the service layer of the Basketball Analytics Platform. Services encapsulate business logic and provide a clean API between the web layer and data models.

## Contents

| File | Description |
|------|-------------|
| `README.md` | This file - services documentation overview |
| `analytics-service.md` | AnalyticsService reference - advanced analytics capabilities |

## Service Layer Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API Layer                                       │
│                   (FastAPI routers, HTTP handling)                          │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │ Depends(get_db) → Session
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Service Layer                                     │
│              (Business logic, validation, orchestration)                     │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Orchestration Services                            │    │
│  │  ┌──────────────────┐                                               │    │
│  │  │ AnalyticsService │ ← Composes other services for analytics       │    │
│  │  └──────────────────┘                                               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      Domain Services                                 │    │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐            │    │
│  │  │ LeagueService │  │  TeamService  │  │ PlayerService │            │    │
│  │  └───────────────┘  └───────────────┘  └───────────────┘            │    │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────────────┐    │    │
│  │  │ SeasonService │  │  GameService  │  │ PlayByPlayService     │    │    │
│  │  └───────────────┘  └───────────────┘  └───────────────────────┘    │    │
│  │  ┌─────────────────────────┐  ┌────────────────────────────────┐    │    │
│  │  │ PlayerGameStatsService  │  │ StatsCalculationService        │    │    │
│  │  │ TeamGameStatsService    │  │ PlayerSeasonStatsService       │    │    │
│  │  └─────────────────────────┘  └────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Infrastructure Services                           │    │
│  │  ┌────────────────┐                                                 │    │
│  │  │ SyncLogService │  ← Tracks data synchronization                  │    │
│  │  └────────────────┘                                                 │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │ SQLAlchemy ORM
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Data Layer                                        │
│                   (SQLAlchemy models, database)                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Service Categories

### Domain Services

Basic CRUD and domain-specific operations for core entities:

- **LeagueService** / **SeasonService**: League and season management
- **TeamService**: Team operations, roster management
- **PlayerService**: Player operations, team history
- **GameService**: Game operations, box score loading
- **PlayByPlayService**: Play-by-play event operations

### Stats Services

Statistics calculation and aggregation:

- **PlayerGameStatsService**: Per-game player statistics
- **TeamGameStatsService**: Per-game team statistics
- **StatsCalculationService**: Calculate season aggregates
- **PlayerSeasonStatsService**: Query season/career stats

### Orchestration Services

Higher-level services that compose domain services:

- **AnalyticsService**: Advanced analytics including clutch time, situational analysis, lineup stats, on/off analysis

### Infrastructure Services

Support services for data operations:

- **SyncLogService**: Track external data sync operations

## Service Composition Pattern

Orchestration services like AnalyticsService compose domain services rather than accessing the database directly:

```python
class AnalyticsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        # Compose domain services
        self.pbp_service = PlayByPlayService(db)
        self.player_stats_service = PlayerGameStatsService(db)
        self.team_stats_service = TeamGameStatsService(db)
        self.season_stats_service = PlayerSeasonStatsService(db)
        self.game_service = GameService(db)
```

This pattern:
- Maintains separation of concerns
- Enables easier testing (mock composed services)
- Promotes code reuse
- Keeps business logic in one place

## Usage in API Layer

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.core import get_db
from src.services import AnalyticsService
from src.schemas import ClutchFilter

router = APIRouter()

@router.get("/games/{game_id}/clutch-events")
def get_clutch_events(
    game_id: UUID,
    time_remaining: int = 300,
    score_margin: int = 5,
    db: Session = Depends(get_db)
):
    service = AnalyticsService(db)
    filter = ClutchFilter(
        time_remaining_seconds=time_remaining,
        score_margin=score_margin
    )
    events = service.get_clutch_events(game_id, filter)
    return {"events": events, "count": len(events)}
```

## Related Documentation

- [src/services/README.md](../../src/services/README.md) - Full service reference
- [src/schemas/README.md](../../src/schemas/README.md) - Request/response schemas
- [Architecture](../architecture.md) - System architecture overview

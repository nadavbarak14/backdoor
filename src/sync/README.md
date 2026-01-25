# Sync

## Purpose

This directory contains external data synchronization logic for the Basketball Analytics Platform. It handles importing data from external APIs (Winner League, Euroleague, etc.) into the local database.

## Contents

| File/Directory | Description |
|----------------|-------------|
| `__init__.py` | Package exports |
| `types.py` | Raw data types for sync (RawSeason, RawTeam, RawGame, etc.) |
| `config.py` | Sync configuration (SyncConfig, SyncSourceConfig) |
| `tracking.py` | Sync tracking to prevent re-syncing (SyncTracker) |
| `exceptions.py` | Sync-specific exception classes |
| `adapters/` | Abstract base classes for data adapters |
| `winner/` | Winner League (Israeli Basketball) data fetching |
| `euroleague/` | Euroleague and EuroCup data fetching |

## Sync Architecture

```
External API  →  Adapter  →  Raw Types  →  Service Layer  →  Database
   (API)        (fetch)    (transform)     (validate)       (store)
                   ↓
              SyncTracker
             (prevent dups)
```

## Components

### Raw Types (`types.py`)

Dataclasses representing data from external sources before transformation:

```python
from src.sync.types import RawSeason, RawTeam, RawGame, RawBoxScore

season = RawSeason(
    external_id="2024-25",
    name="2024-25 Season",
    start_date=date(2024, 10, 1),
    is_current=True
)
```

### Adapters (`adapters/`)

Abstract base classes for fetching data from external sources:

```python
from src.sync.adapters import BaseLeagueAdapter

class WinnerAdapter(BaseLeagueAdapter):
    source_name = "winner"

    async def get_seasons(self) -> list[RawSeason]:
        # Fetch from Winner API
        ...
```

### Sync Tracking (`tracking.py`)

Prevents re-syncing games that have already been imported:

```python
from src.sync.tracking import SyncTracker

tracker = SyncTracker(db_session)

# Check if already synced
if not tracker.is_game_synced("winner", "game-123"):
    # Sync the game
    game = sync_game(...)
    tracker.mark_game_synced("winner", "game-123", game.id)
```

### Configuration (`config.py`)

Configure which sources are enabled and their sync settings:

```python
from src.sync.config import SyncConfig

config = SyncConfig.from_settings()

if config.is_source_enabled("winner"):
    sync_winner_data()
```

### Exceptions (`exceptions.py`)

Sync-specific exceptions for error handling:

```python
from src.sync.exceptions import GameNotFoundError, RateLimitError

try:
    boxscore = await adapter.get_game_boxscore("game-123")
except GameNotFoundError:
    logger.warning("Game not found")
except RateLimitError as e:
    await asyncio.sleep(e.retry_after)
```

## Usage

### Implementing a New Adapter

```python
from src.sync.adapters import BaseLeagueAdapter
from src.sync.types import RawSeason, RawTeam, RawGame, RawBoxScore, RawPBPEvent

class MyLeagueAdapter(BaseLeagueAdapter):
    source_name = "my_league"

    async def get_seasons(self) -> list[RawSeason]:
        response = await self.client.get("/seasons")
        return [RawSeason(...) for s in response["seasons"]]

    async def get_teams(self, season_id: str) -> list[RawTeam]:
        ...

    async def get_schedule(self, season_id: str) -> list[RawGame]:
        ...

    async def get_game_boxscore(self, game_id: str) -> RawBoxScore:
        ...

    async def get_game_pbp(self, game_id: str) -> list[RawPBPEvent]:
        ...

    def is_game_final(self, game: RawGame) -> bool:
        return game.status == "final"
```

### Syncing Data

```python
from src.sync.tracking import SyncTracker
from src.sync.config import SyncConfig

async def sync_games(db: Session, adapter: BaseLeagueAdapter):
    config = SyncConfig.from_settings()
    tracker = SyncTracker(db)

    if not config.is_source_enabled(adapter.source_name):
        return

    # Get schedule
    games = await adapter.get_schedule("2024-25")

    # Filter to unsynced games
    external_ids = [g.external_id for g in games]
    unsynced_ids = tracker.get_unsynced_games(adapter.source_name, external_ids)

    for game in games:
        if game.external_id not in unsynced_ids:
            continue

        if adapter.is_game_final(game):
            boxscore = await adapter.get_game_boxscore(game.external_id)
            # Transform and save...
            tracker.mark_game_synced(adapter.source_name, game.external_id, saved_game.id)
```

## Dependencies

- **Internal**: `src/core/`, `src/models/`, `src/services/`
- **External**: `httpx`

## Related Documentation

- [Adapters README](adapters/README.md)
- [Winner README](winner/README.md)
- [Euroleague README](euroleague/README.md)
- [Services](../services/README.md)
- [Architecture](../../docs/architecture.md)

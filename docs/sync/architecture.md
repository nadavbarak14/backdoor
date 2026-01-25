# Sync Architecture

## Overview

The sync layer imports data from external basketball APIs (Winner League, Euroleague) into the local database. It handles data transformation, deduplication across sources, and tracks sync progress to avoid re-importing data.

## Data Flow

```
┌─────────────────┐
│  API Trigger    │  POST /api/v1/sync/{source}/season/{id}
│  (Manual)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SyncManager    │  Orchestrates the sync process
│                 │  Creates SyncLog, coordinates components
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Adapter        │  Fetches data from external API
│  (Source-specific)│  WinnerAdapter, EuroleagueAdapter
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Mapper         │  Transforms API responses to Raw types
│  (Source-specific)│  RawGame, RawBoxScore, RawPlayerStats
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Entity Syncers │  GameSyncer, TeamSyncer, PlayerSyncer
│                 │  Creates/updates database records
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Deduplication  │  PlayerDeduplicator, TeamMatcher
│                 │  Merges external_ids across sources
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SyncTracker    │  Tracks synced games via Game.external_ids
│                 │  Prevents re-syncing completed games
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Database       │  Game, Player, Team, PlayerGameStats
│                 │  TeamGameStats, PlayByPlayEvent
└─────────────────┘
```

## Key Components

### SyncManager (`src/sync/manager.py`)

The central orchestrator for sync operations:

```python
manager = SyncManager(
    db=db_session,
    adapters={"winner": winner_adapter, "euroleague": euro_adapter},
    config=sync_config
)

# Sync all games for a season
sync_log = await manager.sync_season("winner", "2024-25", include_pbp=True)

# Sync a single game
sync_log = await manager.sync_game("winner", "game-123")
```

**Responsibilities:**
- Coordinates adapters, syncers, and tracking
- Creates and updates SyncLog entries
- Handles errors and rollbacks
- Returns sync operation results

### Adapters (`src/sync/adapters/`)

Abstract interface for fetching data from external sources:

```python
class BaseLeagueAdapter(ABC):
    @abstractmethod
    async def get_seasons(self) -> list[RawSeason]: ...

    @abstractmethod
    async def get_teams(self, season_id: str) -> list[RawTeam]: ...

    @abstractmethod
    async def get_schedule(self, season_id: str) -> list[RawGame]: ...

    @abstractmethod
    async def get_game_boxscore(self, game_id: str) -> RawBoxScore: ...

    @abstractmethod
    async def get_game_pbp(self, game_id: str) -> list[RawPBPEvent]: ...
```

**Implementations:**
- `WinnerAdapter` - Winner League (Israeli Basketball)
- `EuroleagueAdapter` - Euroleague and EuroCup

### Entity Syncers (`src/sync/entities/`)

Transform raw data to database records:

| Syncer | Responsibility |
|--------|----------------|
| `GameSyncer` | Creates Game, PlayerGameStats, TeamGameStats, PlayByPlayEvent |
| `TeamSyncer` | Creates Team, TeamSeason, PlayerTeamHistory |
| `PlayerSyncer` | Creates Player records via PlayerDeduplicator |

### Deduplication (`src/sync/deduplication/`)

Merges entities across data sources:

- **PlayerDeduplicator**: Matches players by external_id, team roster, or biographical data
- **TeamMatcher**: Matches teams by external_id or normalized name

When the same player appears in both Winner and Euroleague, their `external_ids` are merged:

```python
player.external_ids = {"winner": "p123", "euroleague": "PWB"}
```

### SyncTracker (`src/sync/tracking.py`)

Prevents re-syncing completed games:

```python
tracker = SyncTracker(db)

# Check if game already synced
if not tracker.is_game_synced("winner", "game-123"):
    # Sync the game...
    tracker.mark_game_synced("winner", "game-123", game.id)
```

Uses `Game.external_ids` JSONB column to track which external IDs have been imported.

## Avoiding Re-Sync

Games are tracked to prevent duplicate imports:

1. **Before sync**: Check `Game.external_ids` for existing external_id
2. **Batch check**: `get_unsynced_games()` filters a list of external_ids
3. **After sync**: Add external_id to `Game.external_ids`

```python
# Get only games that haven't been synced
all_games = await adapter.get_schedule("2024-25")
final_games = [g for g in all_games if adapter.is_game_final(g)]
external_ids = [g.external_id for g in final_games]
unsynced_ids = tracker.get_unsynced_games("winner", external_ids)
```

## Error Handling

### Per-Game Errors

Individual game failures don't stop the season sync:

```python
for raw_game in unsynced_games:
    try:
        game = game_syncer.sync_game(raw_game, season.id, source)
        # ...
        db.commit()
    except Exception as e:
        db.rollback()
        records_skipped += 1
        print(f"Error syncing game {raw_game.external_id}: {e}")
```

### Sync Log Status

| Status | Description |
|--------|-------------|
| `STARTED` | Sync in progress |
| `COMPLETED` | All records processed successfully |
| `PARTIAL` | Some records skipped due to errors |
| `FAILED` | Fatal error stopped the sync |

### Transient vs Permanent Errors

- **Transient** (network timeout, rate limit): Retry with backoff
- **Permanent** (invalid data, missing team): Log and skip record

## Sync Log Tracking

Every sync operation creates a SyncLog entry:

```python
sync_log = sync_log_service.start_sync(
    source="winner",
    entity_type="season",
    season_id=season.id
)

# On success
sync_log_service.complete_sync(
    sync_id=sync_log.id,
    records_processed=150,
    records_created=10,
    records_updated=0,
    records_skipped=140
)

# On failure
sync_log_service.fail_sync(
    sync_id=sync_log.id,
    error_message="API timeout",
    error_details={"endpoint": "/games"}
)
```

## Configuration

Enable/disable sources in settings:

```python
# src/sync/config.py
config = SyncConfig.from_settings()

if config.is_source_enabled("winner"):
    await manager.sync_season("winner", "2024-25")
```

Source configuration includes:
- `enabled` - Whether source is active
- `auto_sync_enabled` - Whether to run scheduled syncs
- `sync_interval_minutes` - How often to check for new games

## Related Documentation

- [Adding a New Source](adding-new-source.md)
- [Field Mappings](field-mappings.md)
- [Deduplication Strategy](deduplication.md)
- [Sync API Reference](../api/sync.md)
- [Source Code](../../src/sync/README.md)

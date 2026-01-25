# Sync Adapters

## Purpose

This directory contains abstract base classes and interfaces for data sync adapters. Adapters are responsible for fetching raw data from external basketball data sources and converting it to our standardized raw data types.

## Contents

| File | Description |
|------|-------------|
| `__init__.py` | Package exports for adapter base classes |
| `base.py` | Abstract base classes `BaseLeagueAdapter` and `BasePlayerInfoAdapter` |

## Adapter Types

### BaseLeagueAdapter

For fetching league-specific game data:
- Seasons available in the source
- Teams participating in each season
- Game schedules
- Box scores with player statistics
- Play-by-play data

### BasePlayerInfoAdapter

For fetching player biographical information:
- Player details (name, height, birth date, position)
- Player search functionality

## Usage

Concrete adapters should inherit from the appropriate base class:

```python
from src.sync.adapters import BaseLeagueAdapter
from src.sync.types import RawSeason, RawTeam, RawGame, RawBoxScore, RawPBPEvent

class WinnerAdapter(BaseLeagueAdapter):
    """Adapter for Winner League (Israeli Basketball) data."""

    source_name = "winner"

    async def get_seasons(self) -> list[RawSeason]:
        # Fetch from Winner API
        response = await self.client.get("/seasons")
        return [
            RawSeason(
                external_id=s["id"],
                name=s["name"],
                is_current=s["current"]
            )
            for s in response["seasons"]
        ]

    async def get_teams(self, season_id: str) -> list[RawTeam]:
        # Implementation
        ...

    async def get_schedule(self, season_id: str) -> list[RawGame]:
        # Implementation
        ...

    async def get_game_boxscore(self, game_id: str) -> RawBoxScore:
        # Implementation
        ...

    async def get_game_pbp(self, game_id: str) -> list[RawPBPEvent]:
        # Implementation
        ...

    def is_game_final(self, game: RawGame) -> bool:
        return game.status == "final"
```

## Creating a New Adapter

1. Create a new module in the appropriate source directory (e.g., `src/sync/winner/adapter.py`)
2. Inherit from `BaseLeagueAdapter` or `BasePlayerInfoAdapter`
3. Set the `source_name` class attribute
4. Implement all abstract methods
5. Register the adapter in `SyncConfig`

## Dependencies

- **Internal**: `src/sync/types` (raw data types)
- **External**: None (adapters should use their own HTTP clients)

## Related Documentation

- [Sync Types](../types.py) - Raw data types used by adapters
- [Sync Config](../config.py) - Adapter configuration
- [Winner Adapter](../winner/README.md) - Winner League implementation
- [Euroleague Adapter](../euroleague/README.md) - Euroleague implementation

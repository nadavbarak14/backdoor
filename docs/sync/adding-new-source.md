# Adding a New Data Source

This guide explains how to add a new basketball league data source to the sync system.

## Overview

Adding a new source requires:

1. Creating an adapter with client and mapper
2. Implementing the `BaseLeagueAdapter` interface
3. Adding test fixtures
4. Registering the adapter

## Directory Structure

Create a new folder under `src/sync/`:

```
src/sync/new_source/
├── __init__.py      # Package exports
├── README.md        # Documentation
├── adapter.py       # Implements BaseLeagueAdapter
├── client.py        # API communication
├── mapper.py        # Response → RawTypes
└── config.py        # Source-specific configuration (optional)
```

## Step 1: Create the Client

The client handles HTTP communication with the external API:

```python
# src/sync/new_source/client.py
"""
NewSource API Client

Handles communication with the NewSource basketball API.
"""

import httpx
from typing import Any

class NewSourceClient:
    """
    HTTP client for NewSource API.

    Example:
        >>> client = NewSourceClient()
        >>> seasons = await client.get_seasons()
    """

    BASE_URL = "https://api.newsource.com/v1"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers=headers,
                timeout=30.0
            )
        return self._client

    async def get_seasons(self) -> list[dict]:
        """Fetch available seasons."""
        client = await self._get_client()
        response = await client.get("/seasons")
        response.raise_for_status()
        return response.json()["seasons"]

    async def get_teams(self, season_id: str) -> list[dict]:
        """Fetch teams for a season."""
        client = await self._get_client()
        response = await client.get(f"/seasons/{season_id}/teams")
        response.raise_for_status()
        return response.json()["teams"]

    async def get_schedule(self, season_id: str) -> list[dict]:
        """Fetch game schedule for a season."""
        client = await self._get_client()
        response = await client.get(f"/seasons/{season_id}/games")
        response.raise_for_status()
        return response.json()["games"]

    async def get_boxscore(self, game_id: str) -> dict:
        """Fetch box score for a game."""
        client = await self._get_client()
        response = await client.get(f"/games/{game_id}/boxscore")
        response.raise_for_status()
        return response.json()

    async def get_pbp(self, game_id: str) -> list[dict]:
        """Fetch play-by-play events for a game."""
        client = await self._get_client()
        response = await client.get(f"/games/{game_id}/pbp")
        response.raise_for_status()
        return response.json()["events"]

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
```

## Step 2: Create the Mapper

The mapper transforms API responses to normalized `Raw` types:

```python
# src/sync/new_source/mapper.py
"""
NewSource Mapper Module

Maps raw data from NewSourceClient to normalized Raw types.
"""

from datetime import datetime
from src.sync.types import (
    RawSeason, RawTeam, RawGame, RawBoxScore,
    RawPlayerStats, RawPBPEvent, RawPlayerInfo
)

class NewSourceMapper:
    """
    Maps NewSource data to normalized Raw types.

    Example:
        >>> mapper = NewSourceMapper()
        >>> raw_game = mapper.map_game(api_game_data)
    """

    # Event type mapping from API format to our format
    EVENT_TYPE_MAP = {
        "MADE_2PT": "shot",
        "MADE_3PT": "shot",
        "MISS_2PT": "shot",
        "MISS_3PT": "shot",
        "FREE_THROW": "free_throw",
        "REBOUND": "rebound",
        "ASSIST": "assist",
        "TURNOVER": "turnover",
        "STEAL": "steal",
        "BLOCK": "block",
        "FOUL": "foul",
    }

    def map_season(self, data: dict) -> RawSeason:
        """Map season data to RawSeason."""
        return RawSeason(
            external_id=str(data["id"]),
            name=data["name"],
            start_date=datetime.fromisoformat(data["start_date"]).date(),
            end_date=datetime.fromisoformat(data["end_date"]).date() if data.get("end_date") else None,
            is_current=data.get("is_current", False),
        )

    def map_team(self, data: dict) -> RawTeam:
        """Map team data to RawTeam."""
        return RawTeam(
            external_id=str(data["id"]),
            name=data["name"],
            short_name=data.get("abbreviation"),
        )

    def map_game(self, data: dict) -> RawGame:
        """Map game data to RawGame."""
        return RawGame(
            external_id=str(data["id"]),
            home_team_external_id=str(data["home_team_id"]),
            away_team_external_id=str(data["away_team_id"]),
            game_date=datetime.fromisoformat(data["date"]),
            status=data["status"].lower(),
            home_score=data.get("home_score"),
            away_score=data.get("away_score"),
        )

    def map_player_stats(self, data: dict, team_id: str) -> RawPlayerStats:
        """Map player statistics to RawPlayerStats."""
        return RawPlayerStats(
            player_external_id=str(data["player_id"]),
            player_name=data["player_name"],
            team_external_id=team_id,
            minutes_played=self._parse_minutes(data.get("minutes", "0:00")),
            is_starter=data.get("is_starter", False),
            points=data.get("points", 0),
            field_goals_made=data.get("fgm", 0),
            field_goals_attempted=data.get("fga", 0),
            two_pointers_made=data.get("fg2m", 0),
            two_pointers_attempted=data.get("fg2a", 0),
            three_pointers_made=data.get("fg3m", 0),
            three_pointers_attempted=data.get("fg3a", 0),
            free_throws_made=data.get("ftm", 0),
            free_throws_attempted=data.get("fta", 0),
            offensive_rebounds=data.get("oreb", 0),
            defensive_rebounds=data.get("dreb", 0),
            total_rebounds=data.get("reb", 0),
            assists=data.get("ast", 0),
            turnovers=data.get("tov", 0),
            steals=data.get("stl", 0),
            blocks=data.get("blk", 0),
            personal_fouls=data.get("pf", 0),
            plus_minus=data.get("plus_minus", 0),
            efficiency=data.get("eff", 0),
        )

    def map_boxscore(self, data: dict) -> RawBoxScore:
        """Map boxscore data to RawBoxScore."""
        game = self.map_game(data["game"])

        home_players = [
            self.map_player_stats(p, game.home_team_external_id)
            for p in data["home_players"]
        ]
        away_players = [
            self.map_player_stats(p, game.away_team_external_id)
            for p in data["away_players"]
        ]

        return RawBoxScore(
            game=game,
            home_players=home_players,
            away_players=away_players,
        )

    def map_pbp_event(self, data: dict, event_num: int) -> RawPBPEvent:
        """Map play-by-play event to RawPBPEvent."""
        event_type = self.EVENT_TYPE_MAP.get(
            data["type"], data["type"].lower()
        )

        success = None
        if data["type"].startswith("MADE"):
            success = True
        elif data["type"].startswith("MISS"):
            success = False

        return RawPBPEvent(
            event_number=event_num,
            period=data["period"],
            clock=data["clock"],
            event_type=event_type,
            player_name=data.get("player_name"),
            team_external_id=str(data["team_id"]) if data.get("team_id") else None,
            success=success,
            coord_x=data.get("x"),
            coord_y=data.get("y"),
            related_event_numbers=None,
        )

    def _parse_minutes(self, minutes_str: str) -> int:
        """Parse 'MM:SS' to total seconds."""
        try:
            parts = minutes_str.split(":")
            return int(parts[0]) * 60 + int(parts[1])
        except (ValueError, IndexError):
            return 0
```

## Step 3: Create the Adapter

The adapter implements the `BaseLeagueAdapter` interface:

```python
# src/sync/new_source/adapter.py
"""
NewSource Adapter Module

Implements BaseLeagueAdapter for NewSource basketball data.
"""

from src.sync.adapters.base import BaseLeagueAdapter
from src.sync.types import (
    RawSeason, RawTeam, RawGame, RawBoxScore, RawPBPEvent
)
from src.sync.new_source.client import NewSourceClient
from src.sync.new_source.mapper import NewSourceMapper

class NewSourceAdapter(BaseLeagueAdapter):
    """
    Adapter for NewSource basketball API.

    Example:
        >>> adapter = NewSourceAdapter()
        >>> seasons = await adapter.get_seasons()
    """

    source_name = "new_source"

    def __init__(self, api_key: str | None = None):
        self.client = NewSourceClient(api_key)
        self.mapper = NewSourceMapper()

    async def get_seasons(self) -> list[RawSeason]:
        """Fetch available seasons."""
        data = await self.client.get_seasons()
        return [self.mapper.map_season(s) for s in data]

    async def get_teams(self, season_id: str) -> list[RawTeam]:
        """Fetch teams for a season."""
        data = await self.client.get_teams(season_id)
        return [self.mapper.map_team(t) for t in data]

    async def get_schedule(self, season_id: str) -> list[RawGame]:
        """Fetch game schedule for a season."""
        data = await self.client.get_schedule(season_id)
        return [self.mapper.map_game(g) for g in data]

    async def get_game_boxscore(self, game_id: str) -> RawBoxScore:
        """Fetch box score for a game."""
        data = await self.client.get_boxscore(game_id)
        return self.mapper.map_boxscore(data)

    async def get_game_pbp(self, game_id: str) -> list[RawPBPEvent]:
        """Fetch play-by-play events for a game."""
        data = await self.client.get_pbp(game_id)
        return [
            self.mapper.map_pbp_event(e, i)
            for i, e in enumerate(data, start=1)
        ]

    def is_game_final(self, game: RawGame) -> bool:
        """Check if game is completed."""
        return game.status == "final"

    async def close(self) -> None:
        """Close the client connection."""
        await self.client.close()
```

## Step 4: Add Package Exports

```python
# src/sync/new_source/__init__.py
"""
NewSource Sync Package

Provides adapter and client for NewSource basketball API.
"""

from src.sync.new_source.adapter import NewSourceAdapter
from src.sync.new_source.client import NewSourceClient
from src.sync.new_source.mapper import NewSourceMapper

__all__ = [
    "NewSourceAdapter",
    "NewSourceClient",
    "NewSourceMapper",
]
```

## Step 5: Add Test Fixtures

Create sample API responses for testing:

```
tests/fixtures/new_source/
├── seasons.json
├── teams.json
├── schedule.json
├── boxscore.json
└── pbp.json
```

Example `tests/fixtures/new_source/boxscore.json`:

```json
{
  "game": {
    "id": "12345",
    "home_team_id": "100",
    "away_team_id": "101",
    "date": "2024-01-15T19:30:00",
    "status": "final",
    "home_score": 95,
    "away_score": 88
  },
  "home_players": [
    {
      "player_id": "p1",
      "player_name": "John Smith",
      "is_starter": true,
      "minutes": "32:15",
      "points": 22,
      "fgm": 8,
      "fga": 15
    }
  ],
  "away_players": []
}
```

## Step 6: Register the Adapter

Add the adapter to the available adapters:

```python
# In your application setup or src/sync/config.py

from src.sync.new_source import NewSourceAdapter

# When creating SyncManager
adapters = {
    "winner": WinnerAdapter(),
    "euroleague": EuroleagueAdapter(),
    "new_source": NewSourceAdapter(api_key="your-key"),
}

manager = SyncManager(
    db=db_session,
    adapters=adapters,
    config=sync_config
)
```

Update `SyncConfig` to include the new source:

```python
# src/sync/config.py
class SyncConfig:
    def __init__(self):
        self.sources = {
            "winner": SyncSourceConfig(...),
            "euroleague": SyncSourceConfig(...),
            "new_source": SyncSourceConfig(
                enabled=True,
                auto_sync_enabled=False,
                sync_interval_minutes=60,
            ),
        }
```

## Step 7: Add README Documentation

Create `src/sync/new_source/README.md`:

```markdown
# NewSource Adapter

## API Structure

- Base URL: https://api.newsource.com/v1
- Authentication: Bearer token
- Rate limits: 100 requests/minute

## Endpoints Used

| Endpoint | Purpose |
|----------|---------|
| GET /seasons | List available seasons |
| GET /seasons/{id}/teams | Team rosters |
| GET /seasons/{id}/games | Game schedule |
| GET /games/{id}/boxscore | Box score |
| GET /games/{id}/pbp | Play-by-play |

## Field Mappings

See [Field Mappings](../../../../docs/sync/field-mappings.md)
```

## Step 8: Write Tests

```python
# tests/unit/sync/new_source/test_mapper.py
import pytest
from src.sync.new_source.mapper import NewSourceMapper

class TestNewSourceMapper:
    def test_map_game(self):
        mapper = NewSourceMapper()
        data = {
            "id": "12345",
            "home_team_id": "100",
            "away_team_id": "101",
            "date": "2024-01-15T19:30:00",
            "status": "final",
            "home_score": 95,
            "away_score": 88,
        }

        game = mapper.map_game(data)

        assert game.external_id == "12345"
        assert game.home_score == 95
        assert game.status == "final"
```

## Checklist

- [ ] Client implementation with all API calls
- [ ] Mapper with all field transformations
- [ ] Adapter implementing BaseLeagueAdapter
- [ ] Package `__init__.py` with exports
- [ ] Test fixtures for all endpoints
- [ ] Unit tests for mapper
- [ ] Integration tests for adapter
- [ ] README.md documentation
- [ ] Registered in SyncConfig
- [ ] Field mappings documented

## Related Documentation

- [Sync Architecture](architecture.md)
- [Field Mappings](field-mappings.md)
- [BaseLeagueAdapter](../../src/sync/adapters/README.md)

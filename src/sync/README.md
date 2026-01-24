# Sync

## Purpose

This directory contains external data synchronization logic for the Basketball Analytics Platform. It handles importing data from external APIs (like the NBA API) into the local database.

## Contents

| File/Directory | Description |
|----------------|-------------|
| `__init__.py` | Package exports |
| `base.py` | Base sync client with common functionality |
| `nba/` | NBA API integration (future) |
| `scheduler.py` | Sync job scheduling (future) |

## Sync Architecture

```
External API  →  Sync Client  →  Service Layer  →  Database
   (NBA)         (fetch)        (transform)       (store)
```

## Sync Client Pattern

```python
import httpx
from src.core.config import settings

class NBAClient:
    """Client for NBA API data fetching."""

    BASE_URL = "https://api.nba.com"

    def __init__(self):
        self.client = httpx.Client(
            base_url=self.BASE_URL,
            timeout=30.0
        )

    def get_players(self, season: str) -> list[dict]:
        """Fetch all players for a season."""
        response = self.client.get(f"/players/{season}")
        response.raise_for_status()
        return response.json()["players"]

    def get_games(self, date: str) -> list[dict]:
        """Fetch games for a specific date."""
        response = self.client.get(f"/games/{date}")
        response.raise_for_status()
        return response.json()["games"]
```

## Sync Job Pattern

```python
from sqlalchemy.orm import Session
from src.sync.nba.client import NBAClient
from src.services.player import PlayerService

class PlayerSync:
    """Sync players from NBA API."""

    def __init__(self, db: Session):
        self.db = db
        self.client = NBAClient()
        self.service = PlayerService(db)

    def sync_all(self, season: str) -> int:
        """
        Sync all players for a season.

        Returns:
            Number of players synced
        """
        players = self.client.get_players(season)
        count = 0
        for player_data in players:
            self.service.upsert(player_data)
            count += 1
        self.db.commit()
        return count
```

## Usage

```python
from src.sync.nba.player_sync import PlayerSync

# In a scheduled job or management command
with SessionLocal() as db:
    sync = PlayerSync(db)
    count = sync.sync_all("2024-25")
    print(f"Synced {count} players")
```

## Dependencies

- **Internal**: `src/core/`, `src/services/`
- **External**: `httpx`

## Related Documentation

- [Services](../services/README.md)
- [Architecture](../../docs/architecture.md)

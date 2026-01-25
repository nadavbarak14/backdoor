# iBasketball Sync Module

## Purpose

This module provides data fetching and synchronization capabilities for iBasketball.co.il, which hosts Israeli basketball league data (Liga Leumit, Liga Alef). The site uses the SportsPress WordPress plugin which exposes game data via a REST API.

## Contents

| File | Description |
|------|-------------|
| `__init__.py` | Public exports for the module |
| `adapter.py` | Main adapter implementing `BaseLeagueAdapter` and `BasePlayerInfoAdapter` |
| `api_client.py` | REST API client for SportsPress `/wp-json/sportspress/v2/` endpoints |
| `scraper.py` | HTML scraper for PBP data and player profiles |
| `mapper.py` | Data transformation from API/scraper formats to `Raw*` types |
| `config.py` | Configuration for leagues, URLs, rate limits, and timeouts |
| `exceptions.py` | Custom exception classes for error handling |
| `README.md` | This documentation file |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                       IBasketballAdapter                             │
│   (Implements BaseLeagueAdapter + BasePlayerInfoAdapter)             │
│                                                                      │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │
│   │ IBasketballApi  │  │ IBasketball     │  │ IBasketballMapper   │ │
│   │ Client          │  │ Scraper         │  │                     │ │
│   │ (REST API)      │  │ (HTML)          │  │ (Transformation)    │ │
│   └────────┬────────┘  └────────┬────────┘  └─────────────────────┘ │
│            │                    │                                    │
│            ▼                    ▼                                    │
│   ┌─────────────────────────────────────────┐                       │
│   │           SyncCache (Database)          │                       │
│   │   (SHA-256 change detection, caching)   │                       │
│   └─────────────────────────────────────────┘                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Supported Leagues

| League | Key | SportsPress ID |
|--------|-----|----------------|
| Liga Leumit | `liga_leumit` | 119474 |
| Liga Alef | `liga_al` | 119473 |

## Usage

### Basic Usage with Adapter

```python
from sqlalchemy.orm import Session
from src.sync.ibasketball import (
    IBasketballAdapter,
    IBasketballApiClient,
    IBasketballScraper,
    IBasketballMapper,
)

db = SessionLocal()

# Create components
client = IBasketballApiClient(db)
scraper = IBasketballScraper(db)
mapper = IBasketballMapper()

# Create adapter
adapter = IBasketballAdapter(client, mapper, scraper)

# Set active league
adapter.set_league("liga_leumit")

# Fetch data
seasons = await adapter.get_seasons()
teams = await adapter.get_teams(seasons[0].external_id)
games = await adapter.get_schedule(seasons[0].external_id)

# Get boxscore for a completed game
final_games = [g for g in games if adapter.is_game_final(g)]
if final_games:
    boxscore = await adapter.get_game_boxscore(final_games[0].external_id)
```

### Using the API Client Directly

```python
from src.sync.ibasketball import IBasketballApiClient

with IBasketballApiClient(db) as client:
    # Fetch all events for Liga Leumit
    result = client.fetch_all_events("119474")
    print(f"Found {len(result.data)} events")

    # Fetch single event with boxscore
    event = client.fetch_event("123456")
    print(f"Teams: {event.data.get('teams')}")
```

### Using the Scraper

```python
from src.sync.ibasketball import IBasketballScraper

with IBasketballScraper(db) as scraper:
    # Fetch play-by-play
    pbp = scraper.fetch_game_pbp("team-a-vs-team-b")
    print(f"Found {len(pbp.events)} PBP events")

    # Fetch player profile
    profile = scraper.fetch_player("john-smith")
    print(f"Player: {profile.name}")
```

### Switching Leagues

```python
# Get available leagues
leagues = adapter.get_available_leagues()
# ['liga_al', 'liga_leumit']

# Switch to Liga Alef
adapter.set_league("liga_al")

# Now all operations use Liga Alef
seasons = await adapter.get_seasons()
```

## API Endpoints

The module uses the SportsPress REST API:

| Endpoint | Purpose |
|----------|---------|
| `/wp-json/sportspress/v2/events?leagues={id}` | List events/games |
| `/wp-json/sportspress/v2/events/{id}` | Single event with boxscore |
| `/wp-json/sportspress/v2/tables?leagues={id}` | League standings |
| `/wp-json/sportspress/v2/teams` | Team list |

## Data Mapping

### Stat Field Mapping

SportsPress stats are mapped to normalized field names:

```python
STAT_MAPPING = {
    "pts": "points",
    "fgm": "field_goals_made",
    "fga": "field_goals_attempted",
    "threepm": "three_pointers_made",
    "ftm": "free_throws_made",
    "reb": "total_rebounds",
    "ast": "assists",
    "stl": "steals",
    "blk": "blocks",
    "to": "turnovers",
    "pf": "personal_fouls",
}
```

### PBP Event Mapping

Hebrew PBP event types are mapped to normalized types:

```python
PBP_EVENT_MAP = {
    "קליעה": "shot",          # Made shot
    "החטאה": "shot",           # Missed shot
    "ריבאונד": "rebound",
    "אסיסט": "assist",
    "חטיפה": "steal",
    "איבוד": "turnover",
    "חסימה": "block",
    "עבירה": "foul",
}
```

## Rate Limiting

The module respects the site's servers with configurable rate limits:

| Type | Default Rate | Burst Size |
|------|-------------|------------|
| API requests | 2.0 req/sec | 5 |
| HTML scraping | 0.5 req/sec | 2 |

## Caching

All fetched data is cached in the `SyncCache` database table with:
- SHA-256 content hashing for change detection
- Source identifier: `"ibasketball"`
- Resource types: `events`, `event`, `standings`, `teams`, `game_pbp`, `player_page`

## Dependencies

### Internal
- `src.sync.adapters.base` - Base adapter interfaces
- `src.sync.types` - Raw data type definitions
- `src.sync.winner.rate_limiter` - Shared rate limiter
- `src.models.sync_cache` - Cache model

### External
- `httpx` - HTTP client
- `beautifulsoup4` - HTML parsing
- `sqlalchemy` - Database ORM

## Error Handling

Custom exceptions for specific error scenarios:

```python
from src.sync.ibasketball.exceptions import (
    IBasketballError,           # Base exception
    IBasketballAPIError,        # HTTP/API failures
    IBasketballParseError,      # Parsing failures
    IBasketballRateLimitError,  # Rate limit exceeded
    IBasketballTimeoutError,    # Request timeout
    IBasketballLeagueNotFoundError,  # Invalid league key
)
```

## Related Documentation

- [Sync Layer Overview](../README.md)
- [Base Adapter Interfaces](../adapters/README.md)
- [Raw Data Types](../types.py)
- [Winner Adapter](../winner/README.md) - Reference implementation

# Winner League Sync

## Purpose

This module provides the data fetching layer for Winner League (Israeli Basketball Premier League). It handles fetching and caching raw data from Winner League APIs and HTML pages.

## Contents

| File | Description |
|------|-------------|
| `__init__.py` | Package exports |
| `config.py` | WinnerConfig settings (rate limits, timeouts, URLs) |
| `exceptions.py` | Custom exceptions for Winner League operations |
| `rate_limiter.py` | Token bucket rate limiter for request throttling |
| `client.py` | WinnerClient for JSON API fetching (games, boxscores, PBP) |
| `scraper.py` | WinnerScraper for HTML page scraping (players, teams) |

## Data Sources

| Endpoint | Type | Purpose |
|----------|------|---------|
| `basket.co.il/pbp/json/games_all.json` | JSON | All current season games |
| `segevstats.com/get_team_score.php?game_id=X` | JSON | Game boxscore |
| `segevstats.com/get_team_action.php?game_id=X` | JSON | Play-by-play events |
| `basket.co.il/player.asp?PlayerId=X` | HTML | Player profile |
| `basket.co.il/team.asp?TeamId=X` | HTML | Team roster |
| `basket.co.il/results.asp?cYear=X` | HTML | Historical results |

## Usage

### Fetching Game Data

```python
from sqlalchemy.orm import Session
from src.sync.winner import WinnerClient

def fetch_games(db: Session):
    with WinnerClient(db) as client:
        # Fetch all games for current season
        result = client.fetch_games_all()
        print(f"Fetched {len(result.data.get('games', []))} games")
        print(f"Data changed: {result.changed}")

        # Fetch boxscore for a specific game
        boxscore = client.fetch_boxscore("12345")
        print(f"Home score: {boxscore.data.get('home_score')}")

        # Fetch play-by-play
        pbp = client.fetch_pbp("12345")
        print(f"Events: {len(pbp.data.get('events', []))}")
```

### Scraping Player/Team Data

```python
from sqlalchemy.orm import Session
from src.sync.winner import WinnerScraper

def fetch_player_info(db: Session):
    with WinnerScraper(db) as scraper:
        # Fetch player profile
        profile = scraper.fetch_player("54321")
        print(f"Player: {profile.name}")
        print(f"Team: {profile.team_name}")

        # Fetch team roster
        roster = scraper.fetch_team_roster("100")
        for player in roster.players:
            print(f"#{player.jersey_number}: {player.name}")
```

### Custom Configuration

```python
from src.sync.winner import WinnerClient, WinnerConfig

config = WinnerConfig(
    api_requests_per_second=1.0,  # Slower rate
    scrape_requests_per_second=0.25,  # Even slower for HTML
    request_timeout=60.0,  # Longer timeout
)

with WinnerClient(db, config=config) as client:
    result = client.fetch_games_all()
```

## Caching

All fetched data is stored in the `sync_cache` table:
- **Checksum-based**: SHA-256 hash detects changes without full comparison
- **Automatic**: Cache is checked before making HTTP requests
- **Force refresh**: Use `force=True` to bypass cache

```python
# Normal fetch (uses cache if available)
result = client.fetch_boxscore("12345")

# Force refresh from API
result = client.fetch_boxscore("12345", force=True)

# Check if data changed
if result.changed:
    print("New data available!")
```

## Rate Limiting

The module uses a token bucket algorithm for rate limiting:
- **API requests**: 2 requests/second (configurable)
- **HTML scraping**: 0.5 requests/second (configurable)
- **Burst allowance**: Allows short bursts up to bucket size
- **Exponential backoff**: Automatic retry with increasing delays

## Dependencies

- **Internal**: `src/core/`, `src/models/sync_cache`
- **External**: `httpx`, `beautifulsoup4`

## Related Documentation

- [Sync Package](../README.md)
- [SyncCache Model](../../models/README.md)

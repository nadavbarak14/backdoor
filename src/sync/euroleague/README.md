# Euroleague Sync

Data fetching layer for Euroleague and EuroCup basketball competitions.

## Purpose

Provides clients for fetching data from Euroleague APIs with caching support:

- **EuroleagueClient**: Wraps the `euroleague-api` Python package for game data, boxscores, play-by-play, standings
- **EuroleagueDirectClient**: Direct HTTP client for teams/players XML APIs and live game JSON APIs

## Contents

| File | Description |
|------|-------------|
| `__init__.py` | Package exports |
| `config.py` | Configuration settings (endpoints, rate limits, competition selection) |
| `exceptions.py` | Custom exception classes |
| `client.py` | Client wrapping euroleague-api package with caching |
| `direct_client.py` | Direct HTTP client for APIs not covered by the package |

## Data Sources

### 1. euroleague-api Package (EuroleagueClient)

Returns pandas DataFrames, automatically converted to dicts for caching.

| Data | Method |
|------|--------|
| Season games | `fetch_season_games(season)` |
| Game metadata | `fetch_game_metadata(season, gamecode)` |
| Boxscore | `fetch_game_boxscore(season, gamecode)` |
| Play-by-play | `fetch_game_pbp(season, gamecode)` |
| PBP with lineups | `fetch_game_pbp_with_lineups(season, gamecode)` |
| Shot data | `fetch_game_shots(season, gamecode)` |
| Standings | `fetch_standings(season, round_number)` |
| Player leaders | `fetch_player_leaders(season, stat_category)` |

### 2. Direct APIs (EuroleagueDirectClient)

#### Teams API (XML)
```
https://api-live.euroleague.net/v1/teams?seasonCode=E2024
```
Returns teams with full rosters including player positions and nationalities.

#### Players API (XML)
```
https://api-live.euroleague.net/v1/players?playerCode=011987&seasonCode=E2024
```
Returns player profiles with height, birthdate, and season stats.

#### Live Game API (JSON)
```
https://live.euroleague.net/api/{Endpoint}?gamecode=1&seasoncode=E2024
```
Endpoints: `Header`, `Boxscore`, `PlaybyPlay`, `Points`, `Comparison`

## Usage

### Basic Usage

```python
from sqlalchemy.orm import Session
from src.sync.euroleague import EuroleagueClient, EuroleagueDirectClient

db = SessionLocal()

# Fetch season games
with EuroleagueClient(db) as client:
    result = client.fetch_season_games(2024)
    print(f"Found {len(result.data)} games")

    # Check if data changed
    if result.changed:
        print("New data available!")

    # Fetch boxscore
    boxscore = client.fetch_game_boxscore(2024, gamecode=1)
    for player in boxscore.data[:5]:
        print(f"{player['Player']}: {player['Points']} pts")

# Fetch teams with rosters
with EuroleagueDirectClient(db) as client:
    teams = client.fetch_teams(2024)
    for team in teams.data:
        print(f"{team['name']}: {len(team['players'])} players")

    # Fetch player profile
    player = client.fetch_player('011987', 2024)
    print(f"Height: {player.data['height']}m")
```

### EuroCup

```python
from src.sync.euroleague import EuroleagueConfig, EuroleagueClient

# Configure for EuroCup (competition='U')
config = EuroleagueConfig(competition='U')

with EuroleagueClient(db, config=config) as client:
    result = client.fetch_season_games(2024)
    print(f"EuroCup games: {len(result.data)}")
```

### Force Refresh

```python
# Bypass cache and fetch fresh data
result = client.fetch_season_games(2024, force=True)
```

## Configuration

```python
from src.sync.euroleague import EuroleagueConfig

config = EuroleagueConfig(
    competition='E',           # 'E' = Euroleague, 'U' = EuroCup
    requests_per_second=2.0,   # Rate limit
    request_timeout=30.0,      # HTTP timeout
    max_retries=3,             # Retry attempts
)
```

## Caching

All data is cached in the `SyncCache` table with:
- SHA-256 checksums for change detection
- `changed` flag indicates if data differs from cache
- `from_cache` flag indicates if served without API request

## Dependencies

- **Internal**: `src.models.sync_cache`, `src.sync.winner.rate_limiter`
- **External**: `euroleague-api`, `httpx`, `xmltodict`, `pandas`

## Related Documentation

- [Sync Layer Overview](../README.md)
- [Winner Adapter](../winner/README.md)
